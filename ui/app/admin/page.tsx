'use client'

import { useEffect, useRef, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8015'

export default function AdminPage() {
  // IMPORTANT: ALL useState hooks must be declared BEFORE any conditional returns
  const [adminToken, setAdminToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [crawlId, setCrawlId] = useState<string | null>(null)
  const [lines, setLines] = useState<string[]>([])
  const [apiHealth, setApiHealth] = useState<string>("unknown")
  const [starting, setStarting] = useState<boolean>(false)
  const [summary, setSummary] = useState<{ discovered: number, enriched: number, scored: number, durationSec: number, persisted?: boolean } | null>(null)
  const [registryProgress, setRegistryProgress] = useState<{ glama: number, mcpso: number }>({ glama: 0, mcpso: 0 })
  const [startTs, setStartTs] = useState<number | null>(null)
  const [runBackfill, setRunBackfill] = useState<boolean>(false)
  const [persistToDb, setPersistToDb] = useState<boolean>(true)
  const esRef = useRef<EventSource | null>(null)

  // Backfill state
  const [backfillId, setBackfillId] = useState<string | null>(null)
  const [bfLines, setBfLines] = useState<string[]>([])
  const [bfSummary, setBfSummary] = useState<{ seen: number, updated: number, scored: number, llm_calls: number, elapsed_sec: number } | null>(null)
  const [bfBatch, setBfBatch] = useState<number>(25)
  const [bfConc, setBfConc] = useState<number>(1)
  // 0 or blank => all servers
  const [bfMax, setBfMax] = useState<number>(0)

  // Per-registry caps
  const [capGlama, setCapGlama] = useState<number>(0)
  const [capMcpso, setCapMcpso] = useState<number>(0)
  const bfEsRef = useRef<EventSource | null>(null)

  // Helper function to create headers with admin token
  const createAdminHeaders = () => ({
    'X-Admin-Token': adminToken || '',
    'Content-Type': 'application/json'
  })

  // Check admin token after component mounts (client-side only)
  useEffect(() => {
    // Access environment variable only on client side to avoid hydration issues
    const token = process.env.NEXT_PUBLIC_ADMIN_ACCESS_TOKEN
    setAdminToken(token || null)
    setIsLoading(false)
  }, [])

  // API health check effect - runs once when admin token is available
  useEffect(() => {
    if (!adminToken) return
    
    // Ping API health on mount
    (async()=>{
      try {
        const r = await fetch(`${API_BASE}/admin/crawl/status`, {
          headers: createAdminHeaders()
        })
        if (r.ok) {
          setApiHealth('ok')
        } else {
          setApiHealth(`error ${r.status}`)
        }
      } catch (e:any) {
        setApiHealth(`error ${(e&&e.message)||'network'}`)
      }
    })()
  }, [adminToken])

  // Crawl streaming effect - runs when crawlId changes
  useEffect(() => {
    if (!adminToken || !crawlId) return
    
    const params = new URLSearchParams({ crawl_id: String(crawlId) })
    if (adminToken) params.set('token', adminToken)
    const url = `${API_BASE}/admin/crawl/stream?${params.toString()}`
    console.log('🔗 Connecting to EventSource:', url)
    const es = new EventSource(url)
    esRef.current = es
    
    es.onopen = () => {
      console.log('✅ EventSource connected')
      const t = new Date().toLocaleString()
      setLines(prev => [`[${t}] 🔗 EventSource connected successfully`, ...prev].slice(0, 200))
    }
    
    es.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data)
        const ts = new Date((evt.ts || Date.now()/1000) * 1000)
        const tstr = ts.toLocaleString()
        let line: string | null = null
        if (evt.kind === 'started') {
          setStartTs(evt.ts || (Date.now()/1000))
          setSummary(null)
          line = `[${tstr}] 🚀 Crawl started - beginning server discovery...`
        } else if (evt.kind === 'progress') {
          if (evt.data && evt.data.summary) {
            const s = evt.data.summary
            const d = Math.max(0, ((evt.ts || Date.now()/1000) - (startTs || (evt.ts || Date.now()/1000))))
            setSummary({
              discovered: Number(s.discovered_count || 0),
              enriched: Number(s.enriched_count || 0),
              scored: Number(s.scored_count || 0),
              durationSec: Math.round(d),
              persisted: Boolean(s.persisted),
            })
            line = `[${tstr}] Summary: discovered=${s.discovered_count} enriched=${s.enriched_count} scored=${s.scored_count} persisted=${Boolean(s.persisted)}`
          } else if (evt.data && evt.data.heartbeat) {
            line = `[${tstr}] ⏱️ Heartbeat - crawl active`
          } else if (evt.data && evt.data.crawl_step) {
            const s = evt.data.crawl_step
            if (s.phase === 'crawl_complete') {
              line = `[${tstr}] 🎯 Crawl complete! Discovered ${s.discovered_count} servers - starting enrichment...`
            } else if (s.phase === 'enrichment_started') {
              line = `[${tstr}] ⚙️ Starting enrichment phase for ${s.total_items} servers...`
            } else if (s.phase === 'scoring_started') {
              line = `[${tstr}] 🔒 Starting security scoring for ${s.total_items} servers...`
            } else if (s.phase === 'database_write_started') {
              line = `[${tstr}] 💾 Writing ${s.total_items} servers to database...`
            } else if (s.phase === 'database_write_complete') {
              line = `[${tstr}] ✅ Database write complete! Saved ${s.persisted_servers} servers + ${s.persisted_scores} scores`
            } else if (s.phase === 'immediate_persist') {
              line = `[${tstr}] ${s.message || `💾 Saved ${s.persisted_count} servers from ${s.registry} to database`}`
            } else if (s.phase === 'periodic_persist') {
              line = `[${tstr}] 💾 Periodic save: ${s.persisted} servers (total ${s.total})`
            } else if (s.phase === 'persist_error') {
              line = `[${tstr}] ${s.message || `⚠️ Failed to save ${s.registry} servers`}`
            } else if (s.phase === 'pipeline_complete') {
              line = `[${tstr}] 🎉 Pipeline complete! ${s.discovered} discovered → ${s.enriched} enriched → ${s.scored} scored → ${s.persisted ? 'persisted' : 'not persisted'}`
            } else if (s.phase === 'processing_details' && s.registry === 'glama') {
              line = `[${tstr}] 🔍 Glama: processing details ${s.processed}/${s.total_links} (found ${s.found} servers)`
            } else if (s.registry && s.found !== undefined) {
              // Update per-registry progress
              const registryName = s.registry.toLowerCase().includes('glama') ? 'glama' : 
                                  s.registry.toLowerCase().includes('mcp.so') ? 'mcpso' : s.registry
              if (registryName === 'glama' || registryName === 'mcpso') {
                setRegistryProgress(prev => ({
                  ...prev,
                  [registryName]: Number(s.found)
                }))
              }
              line = `[${tstr}] ✅ ${s.registry}: collected ${s.found} servers`
            } else if (s.registry && s.cap_reached && s.persisted !== undefined) {
              // Handle immediate DB write when cap is reached
              line = `[${tstr}] ${s.message || `🎯💾 ${s.registry}: Cap reached! Saved ${s.persisted} servers to database`}`
            }
          } else if (evt.data && evt.data.connected) {
            line = `[${tstr}] 🔗 Stream connected - waiting for crawl data...`
          } else if (evt.data && evt.data.status) {
            line = `[${tstr}] 📡 Status: ${evt.data.status}`
          } else if (evt.data && evt.data.backfill) {
            const d = evt.data.backfill
            if (d && d.seen !== undefined) {
              line = `[${tstr}] Backfill progress: seen=${d.seen} updated=${d.updated} scored=${d.scored} llm_calls=${d.llm_calls}`
            }
          } else if (evt.data && evt.data.backfill_summary) {
            const s = evt.data.backfill_summary
            line = `[${tstr}] Backfill summary: seen=${s?.seen} updated=${s?.updated} scored=${s?.scored} llm_calls=${s?.llm_calls} elapsed=${s?.elapsed_sec}s`
          } else {
            // Debug: catch any unhandled progress events
            line = `[${tstr}] 🔍 DEBUG: ${JSON.stringify(evt.data)}`
          }
        } else if (evt.kind === 'done') {
          line = `[${tstr}] ✅ Crawl completed successfully!`
        } else if (evt.kind === 'error') {
          line = `[${tstr}] ❌ Error: ${evt.data?.message || 'unknown error'}`
        }
        if (line) setLines((prev) => [line, ...prev].slice(0, 200))
        if (evt.kind === 'done' || evt.kind === 'error') {
          es.close()
          esRef.current = null
          // Reset registry progress on completion
          if (evt.kind === 'done') {
            setTimeout(() => setRegistryProgress({ glama: 0, mcpso: 0 }), 5000)
          }
        }
      } catch {}
    }
    es.onerror = (error) => {
      console.error('❌ EventSource error:', error)
      const t = new Date().toLocaleString()
      setLines(prev => [`[${t}] ❌ EventSource connection error - retrying...`, ...prev].slice(0, 200))
      es.close()
      esRef.current = null
      // Simple auto-reconnect with backoff up to 10s
      let delay = 1000
      const maxDelay = 10000
      const retry = () => {
        if (!crawlId || !adminToken) return
        const params2 = new URLSearchParams({ crawl_id: String(crawlId) })
        params2.set('token', adminToken)
        const url2 = `${API_BASE}/admin/crawl/stream?${params2.toString()}`
        const es2 = new EventSource(url2)
        esRef.current = es2
        es2.onopen = () => {
          const t2 = new Date().toLocaleString()
          setLines(prev => [`[${t2}] 🔁 EventSource reconnected`, ...prev].slice(0, 200))
          delay = 1000
        }
        es2.onerror = () => {
          es2.close()
          esRef.current = null
          delay = Math.min(delay * 2, maxDelay)
          setTimeout(retry, delay)
        }
        es2.onmessage = es.onmessage
      }
      setTimeout(retry, delay)
    }
    return () => {
      es.close()
      esRef.current = null
    }
  }, [crawlId, adminToken, startTs])

  // Show loading during hydration
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-md mx-auto bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <div className="text-blue-500 text-6xl mb-4">⏳</div>
            <h1 className="text-xl font-semibold text-gray-800 mb-2">Loading...</h1>
            <p className="text-gray-600">Checking admin access...</p>
          </div>
        </div>
      </div>
    )
  }

  // Show access denied if no token
  if (!adminToken) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-md mx-auto bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <div className="text-red-500 text-6xl mb-4">🔒</div>
            <h1 className="text-xl font-semibold text-gray-800 mb-2">Access Denied</h1>
            <p className="text-gray-600 mb-4">Admin access not configured.</p>
            <p className="text-sm text-gray-500">
              This page is restricted. Contact the administrator for access.
            </p>
          </div>
        </div>
      </div>
    )
  }



  async function start() {
    try {
      setStarting(true)
      // Clear previous run logs for clarity
      setLines([])
      const t = new Date().toLocaleString()
      setLines(prev => [`[${t}] Starting crawl…`, ...prev].slice(0,200))
      // Start a large crawl with persistence and auto-backfill
      const u = new URL(`${API_BASE}/admin/crawl/start`)
      // Explicitly select registries 1 and 2
      u.searchParams.set('enabled_registries', 'registry_1,registry_2')
      // Map UI registry order to backend generic registry params
      u.searchParams.set('max_pages_registry_1', '9999')
      u.searchParams.set('max_pages_registry_2', '9999')
      u.searchParams.set('crawl_concurrency', '8')
      u.searchParams.set('enrich_concurrency', '8')
      u.searchParams.set('score_concurrency', '12')
      u.searchParams.set('persist', String(persistToDb))
      u.searchParams.set('backfill_after', String(Boolean(runBackfill)))
      u.searchParams.set('bf_batch_size', '50')
      u.searchParams.set('bf_enrich_concurrency', '1')
      // optional per-registry caps
      if (capGlama > 0) u.searchParams.set('max_items_registry_1', String(capGlama))
      if (capMcpso > 0) u.searchParams.set('max_items_registry_2', String(capMcpso))
      // omit bf_max_items to run for all
      console.log('🚀 Starting crawl with URL:', u.toString())
      console.log('🔑 Admin headers:', createAdminHeaders())
      
      const resp = await fetch(u.toString(), { 
        method: 'POST',
        headers: createAdminHeaders()
      })
      
      console.log('📡 Start crawl response:', resp.status, resp.statusText)
      
      if (!resp.ok) {
        const txt = await resp.text().catch(()=>`HTTP ${resp.status}`)
        console.error('❌ Start crawl failed:', txt)
        setLines(prev => [`[${t}] Start failed: ${txt}`, ...prev].slice(0,200))
        setStarting(false)
        return
      }
      const json = await resp.json().catch(()=>({}))
      if (!json || !json.crawl_id) {
        setLines(prev => [`[${t}] Start failed: invalid response`, ...prev].slice(0,200))
        setStarting(false)
        return
      }
      setCrawlId(json.crawl_id)
      setLines(prev => [`[${t}] Start accepted: ${json.crawl_id}`, ...prev].slice(0,200))
      setSummary(null)
      setRegistryProgress({ glama: 0, mcpso: 0 })
      setApiHealth('ok')
      setStarting(false)
    } catch (e:any) {
      const t = new Date().toLocaleString()
      setLines(prev => [`[${t}] Start error: ${(e&&e.message)||e}`, ...prev].slice(0,200))
    } finally {
      setStarting(false)
    }
  }

  async function stop() {
    const t = new Date().toLocaleString()
    setLines(prev => [`[${t}] 🛑 Stopping crawl...`, ...prev].slice(0, 200))
    
    try {
      const res = await fetch(`${API_BASE}/admin/crawl/stop`, { 
        method: 'POST',
        headers: createAdminHeaders()
      })
      if (res.ok) {
        setLines(prev => [`[${t}] ✅ Stop request sent successfully`, ...prev].slice(0, 200))
        // Don't close EventSource immediately - wait for cancellation event from backend
      } else {
        setLines(prev => [`[${t}] ❌ Stop request failed: ${res.status}`, ...prev].slice(0, 200))
      }
    } catch (error) {
      setLines(prev => [`[${t}] ❌ Stop request error: ${error}`, ...prev].slice(0, 200))
    }
  }

  // Test API function
  async function testAPI() {
    const t = new Date().toLocaleString()
    setLines(prev => [`[${t}] 🔄 Testing API connection...`, ...prev].slice(0, 200))
    
    try {
      console.log('Testing API with URL:', `${API_BASE}/search?q=&limit=5&offset=0&sort=rank`)
      const res = await fetch(`${API_BASE}/search?q=&limit=5&offset=0&sort=rank`)
      console.log('API Test Response:', res.status, res.ok)
      const data = await res.json()
      console.log('API Test Data:', data?.items?.length, 'items')
      
      const t2 = new Date().toLocaleString()
      if (res.ok) {
        setLines(prev => [`[${t2}] ✅ API Test SUCCESS: ${res.status} - Found ${data?.items?.length || 0} servers`, ...prev].slice(0, 200))
        setApiHealth('ok')
      } else {
        setLines(prev => [`[${t2}] ❌ API Test FAILED: ${res.status} ${res.statusText}`, ...prev].slice(0, 200))
        setApiHealth(`error ${res.status}`)
      }
    } catch (error) {
      console.error('API Test Error:', error)
      const t2 = new Date().toLocaleString()
      setLines(prev => [`[${t2}] ❌ API Test ERROR: ${error}`, ...prev].slice(0, 200))
      setApiHealth(`error network`)
    }
  }

  return (
    <div className="space-y-6">
      {/* API Debug Section */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
        <h3 className="text-lg font-medium text-gray-800 mb-3">API Debug</h3>
        <div className="text-sm space-y-1 mb-3 text-gray-700">
          <div>API_BASE: {API_BASE}</div>
          <div>Admin Token: <span className={adminToken ? 'text-green-600' : 'text-red-600'}>{adminToken ? 'Present' : 'Missing'}</span></div>
          <div>Health: <span className={apiHealth === 'ok' ? 'text-green-600' : 'text-red-600'}>{apiHealth}</span></div>
        </div>
        <button 
          onClick={testAPI} 
          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          Test API
        </button>
      </div>

      {/* Crawl Control Section */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-6 shadow-lg">
        <h2 className="text-lg font-medium text-gray-800 mb-3">Crawl Control</h2>
        <p className="text-sm text-gray-600 mb-4">
          Start a background crawl across configured registries (glama, mcp.so).
          While running, progress events will stream below. You can stop the crawl at any time.
        </p>
        
        <div className="flex items-center gap-3 mb-4">
          <button 
            onClick={start} 
            disabled={starting} 
            className={`px-4 py-2 rounded-lg text-white font-medium transition-colors shadow-sm ${
              starting 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-gray-600 hover:bg-gray-700'
            }`}
          >
            {starting ? 'Starting...' : 'Start Crawl'}
          </button>
          <button 
            onClick={stop} 
            className="px-4 py-2 rounded-lg bg-gray-500 hover:bg-gray-600 text-white font-medium transition-colors shadow-sm"
          >
            Stop
          </button>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={persistToDb} onChange={(e)=>setPersistToDb(e.target.checked)} />
            Save to database
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={runBackfill} onChange={(e)=>setRunBackfill(e.target.checked)} />
            Run backfill after crawl
          </label>
          {crawlId && <span className="text-sm text-green-600 font-medium">Running...</span>}
          <span className="text-sm text-gray-500">API: {apiHealth}</span>
        </div>
        
        <div className="flex items-center gap-4 mb-4 text-sm">
          <label className="flex items-center gap-2">
            Registry 1 Cap
            <input 
              type="number" 
              placeholder="0 = all" 
              value={capGlama} 
              onChange={e=>setCapGlama(parseInt(e.target.value||'0')||0)} 
              className="w-24 border border-gray-300 rounded px-2 py-1"
            />
          </label>
          <label className="flex items-center gap-2">
            Registry 2 Cap
            <input 
              type="number" 
              placeholder="0 = all" 
              value={capMcpso} 
              onChange={e=>setCapMcpso(parseInt(e.target.value||'0')||0)} 
              className="w-24 border border-gray-300 rounded px-2 py-1"
            />
          </label>
          <div className="text-xs text-gray-600 ml-2">
            Total target: {(capGlama || 0) + (capMcpso || 0) || 'unlimited'}
          </div>
        </div>
      </div>
      
      {/* Registry Progress Display */}
      {(registryProgress.glama > 0 || registryProgress.mcpso > 0) && (
        <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
          <h4 className="text-sm font-medium text-gray-800 mb-3">Collection Progress</h4>
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div className="flex justify-between">
              <span>Registry 1:</span>
              <span className="font-mono">
                {registryProgress.glama}{capGlama > 0 ? ` / ${capGlama}` : ''}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Registry 2:</span>
              <span className="font-mono">
                {registryProgress.mcpso}{capMcpso > 0 ? ` / ${capMcpso}` : ''}
              </span>
            </div>
          </div>
          <div className="pt-2 border-t border-gray-200">
            <div className="flex justify-between text-sm font-medium">
              <span>Total Collected:</span>
              <span className="font-mono">
                {registryProgress.glama + registryProgress.mcpso}
                {((capGlama || 0) + (capMcpso || 0)) > 0 ? ` / ${(capGlama || 0) + (capMcpso || 0)}` : ''}
              </span>
            </div>
          </div>
        </div>
      )}
      {summary && (
        <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
          <h4 className="text-lg font-medium text-gray-800 mb-3">Operation Complete</h4>
          <div className="grid grid-cols-3 gap-4 text-sm mb-3">
            <div className="text-center">
              <div className="text-gray-700 font-medium">Discovered</div>
              <div className="text-green-600 font-mono text-xl">{summary.discovered}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Enriched</div>
              <div className="text-blue-600 font-mono text-xl">{summary.enriched}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Scored</div>
              <div className="text-purple-600 font-mono text-xl">{summary.scored}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-200">
            <div className="text-center">
              <div className="text-gray-700 font-medium">Duration</div>
              <div className="text-yellow-600 font-mono">{Math.floor(summary.durationSec/60)}m {summary.durationSec%60}s</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Persisted</div>
              <div className={`font-mono font-bold ${summary.persisted ? 'text-green-600' : 'text-red-600'}`}>
                {summary.persisted ? 'YES' : 'NO'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-lg font-medium text-gray-800">Activity Log</h4>
          <div className="text-xs text-gray-500">Most recent first</div>
        </div>
        <div className="max-h-80 overflow-y-auto space-y-1">
          {lines.map((ln, i) => (
            <div key={i} className="text-xs bg-gray-50 border border-gray-200 p-2 rounded overflow-x-auto font-mono">
              {ln}
            </div>
          ))}
          {lines.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <div className="text-3xl mb-2">📡</div>
              <div className="text-sm">Awaiting activity...</div>
            </div>
          )}
        </div>
      </div>

      <hr className="my-6" />

      {/* Backfill Control Section */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-6 shadow-lg">
        <h2 className="text-lg font-medium text-gray-800 mb-2">Backfill Control</h2>
        <p className="text-sm text-gray-600 mb-3">
          Run post-crawl enrichment + reputation backfill in small batches with low concurrency. Progress will stream below.
        </p>
        
        <div className="flex items-center gap-4 mb-4 text-sm">
          <label className="flex items-center gap-1">
            Batch
            <input 
              type="number" 
              value={bfBatch} 
              onChange={e=>setBfBatch(parseInt(e.target.value||'0')||0)} 
              className="w-20 border border-gray-300 rounded px-2 py-1"
            />
          </label>
          <label className="flex items-center gap-1">
            Concurrency
            <input 
              type="number" 
              value={bfConc} 
              onChange={e=>setBfConc(parseInt(e.target.value||'0')||0)} 
              className="w-24 border border-gray-300 rounded px-2 py-1"
            />
          </label>
          <label className="flex items-center gap-1">
            Max Items
            <input 
              type="number" 
              placeholder="0 = all" 
              value={bfMax} 
              onChange={e=>setBfMax(parseInt(e.target.value||'0')||0)} 
              className="w-28 border border-gray-300 rounded px-2 py-1"
            />
          </label>
          <button 
            onClick={async()=>{
              // start backfill
              const u = new URL(`${API_BASE}/admin/backfill/start`)
              u.searchParams.set('batch_size', String(Math.max(1,bfBatch)))
              u.searchParams.set('enrich_concurrency', String(Math.max(1,bfConc)))
              if (Number(bfMax) > 0) {
                u.searchParams.set('max_items', String(Number(bfMax)))
              }
              const resp = await fetch(u.toString(), {
                method:'POST',
                headers: createAdminHeaders()
              })
              const json = await resp.json()
              setBackfillId(json.backfill_id)
              setBfLines([])
              setBfSummary(null)
              // stream events
              if (bfEsRef.current) { bfEsRef.current.close(); bfEsRef.current = null }
              const qs = new URLSearchParams({ backfill_id: String(json.backfill_id) })
              if (adminToken) qs.set('token', adminToken)
              const es = new EventSource(`${API_BASE}/admin/backfill/stream?${qs.toString()}`)
              bfEsRef.current = es
              es.onmessage = (e)=>{
                try{
                  const evt = JSON.parse(e.data)
                  const ts = new Date((evt.ts||Date.now()/1000)*1000)
                  const tstr = ts.toLocaleString()
                  if (evt.data && evt.data.summary){
                    const s = evt.data.summary
                    setBfSummary({ seen:Number(s.seen||0), updated:Number(s.updated||0), scored:Number(s.scored||0), llm_calls:Number(s.llm_calls||0), elapsed_sec:Number(s.elapsed_sec||0) })
                    setBfLines(prev=>[`[${tstr}] Summary: seen=${s.seen} updated=${s.updated} scored=${s.scored} llm_calls=${s.llm_calls} elapsed=${s.elapsed_sec}s`, ...prev].slice(0,200))
                  } else if (evt.data) {
                    const d = evt.data
                    if (d.seen!==undefined){
                      setBfLines(prev=>[`[${tstr}] Progress: seen=${d.seen} updated=${d.updated} scored=${d.scored} llm_calls=${d.llm_calls}`, ...prev].slice(0,200))
                    } else if (evt.kind === 'started') {
                      setBfLines(prev=>[`[${tstr}] Backfill started`, ...prev].slice(0,200))
                    } else if (evt.kind === 'error') {
                      setBfLines(prev=>[`[${tstr}] Error: ${evt.data?.message||'unknown'}`, ...prev].slice(0,200))
                    } else if (evt.kind === 'done') {
                      setBfLines(prev=>[`[${tstr}] Backfill completed`, ...prev].slice(0,200))
                    }
                  }
                }catch{}
              }
              es.onerror=()=>{ es.close(); bfEsRef.current=null }
            }} 
            className="px-3 py-1 rounded bg-gray-600 text-white hover:bg-gray-700 transition-colors shadow-sm"
          >
            Start Backfill
          </button>
        </div>
      </div>

      {bfSummary && (
        <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
          <h4 className="text-lg font-medium text-gray-800 mb-3">Backfill Summary</h4>
          <div className="grid grid-cols-3 gap-4 text-sm mb-3">
            <div className="text-center">
              <div className="text-gray-700 font-medium">Seen</div>
              <div className="text-purple-600 font-mono text-xl">{bfSummary.seen}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Updated</div>
              <div className="text-green-600 font-mono text-xl">{bfSummary.updated}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Scored</div>
              <div className="text-blue-600 font-mono text-xl">{bfSummary.scored}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-200">
            <div className="text-center">
              <div className="text-gray-700 font-medium">LLM Calls</div>
              <div className="text-yellow-600 font-mono">{bfSummary.llm_calls}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-700 font-medium">Elapsed</div>
              <div className="text-orange-600 font-mono">{Math.floor(bfSummary.elapsed_sec/60)}m {Math.round(bfSummary.elapsed_sec%60)}s</div>
            </div>
          </div>
        </div>
      )}

      {/* Backfill Activity Log */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-lg font-medium text-gray-800">Backfill Log</h4>
          <div className="text-xs text-gray-500">Newest first</div>
        </div>
        <div className="max-h-80 overflow-y-auto space-y-1">
          {bfLines.map((ln, i)=>(
            <div key={i} className="text-xs bg-gray-50 border border-gray-200 p-2 rounded overflow-x-auto font-mono">
              {ln}
            </div>
          ))}
          {bfLines.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <div className="text-3xl mb-2">🔄</div>
              <div className="text-sm">Backfill ready...</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


