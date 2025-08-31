"use client"

import Link from 'next/link'
import { useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8015'

type ServerItem = {
  id: number
  name: string
  registry: string
  description?: string
  homepage_url?: string
  latest_score?: { score_overall?: number }
}

function sanitizeName(raw?: string): string {
  let s = String(raw || '').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  // Split on common separators to drop taglines
  for (const sep of [' — ', ' – ', ' - ', ' | ', ': ']) {
    const i = s.indexOf(sep);
    if (i > 0) { s = s.slice(0, i).trim(); break; }
  }
  // Keep up to "MCP Server" if present early
  const srv = s.match(/^(.*?\bMCP\s*Server)/i);
  if (srv) s = srv[1].trim();
  // If an article starts a descriptive clause later, cut before it
  const art = s.search(/\s+(An|A|The)\s+/);
  if (art > 0 && art < 60) {
    const before = s.slice(0, art).trim();
    if (before.split(' ').length >= 2) s = before;
  }
  // Insert spaces at camel-case boundaries to avoid run-ons
  s = s.replace(/([a-z])([A-Z])/g, '$1 $2');
  // Remove duplicated initial phrase (1-3 words) if it repeats
  const rep = s.match(/^([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2})\s*\1\b/i);
  if (rep) s = rep[1].trim();
  s = s.replace(/\s{2,}/g, ' ').trim();
  return s;
}

function ScoreBadge({ id, initialScore }: { id: number; initialScore?: number | null }) {
  const [score, setScore] = useState<number | null>(
    typeof initialScore === 'number' && Number.isFinite(initialScore) ? Number(initialScore) : null
  )
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        if (score !== null) { setLoaded(true); return }
        const res = await fetch(`${API_BASE}/servers/${id}/score`, { cache: 'no-store' })
        if (!res.ok) {
          setLoaded(true)
          return
        }
        const data = await res.json()
        if (!cancelled) {
          const v = typeof data?.score_overall === 'number' ? data.score_overall : Number(data?.score_overall)
          setScore(Number.isFinite(v) ? v : null)
          setLoaded(true)
        }
      } catch {
        if (!cancelled) setLoaded(true)
      }
    }
    load()
    return () => { cancelled = true }
  }, [id])

  function badgeClasses(v: number | null) {
    if (v == null) return 'bg-gray-100 text-gray-600'
    if (v > 75) return 'bg-green-100 text-green-700'
    if (v >= 70) return 'bg-yellow-100 text-yellow-700'
    return 'bg-red-100 text-red-700'
  }

  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${badgeClasses(score)}`} title={loaded ? (score == null ? 'No score' : `Security score: ${Math.round(score)}/100`) : 'Loading score…'}>
      {loaded ? (score == null ? 'N/A' : `${Math.round(score)}/100`) : '…'}
    </span>
  )
}

export default function HomePage() {
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ServerItem[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [sort, setSort] = useState<'rank' | 'stars' | 'recent' | 'score'>('rank')

  async function runSearch(text: string, nextOffset = 0) {
    setLoading(true)
    try {
      const qs = new URLSearchParams({
        q: text,
        limit: String(limit),
        offset: String(nextOffset),
        sort: sort,
      })
      const res = await fetch(`${API_BASE}/search?${qs.toString()}`)
      const data = await res.json()
      setItems(data.items || [])
      const totalHeader = res.headers.get('x-total-count') || res.headers.get('X-Total-Count')
      setTotal(totalHeader ? Number(totalHeader) : (data.total ?? null))
      setOffset(nextOffset)
    } catch (error) {
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  // Re-run search when sort changes
  useEffect(() => {
    if (items.length > 0) {
      runSearch(q, 0) // Reset to first page when sort changes
    }
  }, [sort])

  useEffect(() => {
    // Use a timeout to ensure hydration is complete
    const timer = setTimeout(() => {
      if (items.length === 0 && !loading) {
        runSearch('', 0)
      }
    }, 100)
    
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200 shadow-lg">
        <div className="max-w-3xl">
          <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-700 via-gray-800 to-gray-700 bg-clip-text text-transparent mb-2">
            🔍 Discover MCP Servers
          </h2>
          <p className="text-gray-700 mb-4 font-medium">
            Search and explore Model Context Protocol servers with comprehensive security analysis and deployment guidance
          </p>
        </div>
        
        {/* Search Bar */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => { if ((e as any).key === 'Enter') runSearch(q, 0) }}
              placeholder="Search servers... (try: github, security, file-system)"
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent shadow-sm"
            />
                          {loading && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <div className="animate-spin h-4 w-4 border-2 border-gray-500 border-t-transparent rounded-full"></div>
              </div>
            )}
          </div>
          <button 
            onClick={() => runSearch(q, 0)} 
            disabled={loading}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors shadow-sm"
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {/* Filters and Results Count */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <span className="text-gray-700 font-medium">Sort by:</span>
              <select
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 bg-white"
                value={sort}
                onChange={(e) => setSort(e.target.value as any)}
              >
                <option value="rank">Relevance</option>
                <option value="score">Security Score</option>
                <option value="recent">Recently Updated</option>
                <option value="stars">GitHub Stars</option>
              </select>
            </label>
          </div>
          {total !== null && (
            <div className="text-gray-600 font-medium">
              {total.toLocaleString()} servers found
            </div>
          )}
        </div>
      </div>
      {/* Results Grid */}
      <div>
        {!loading && items.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <div className="text-gray-400 text-5xl mb-4">🔍</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No servers found</h3>
            <p className="text-gray-500">Try adjusting your search terms or filters</p>
          </div>
        )}
        
        {items.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {items.map((it) => (
              <div key={it.id} className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-lg transition-all duration-200 overflow-hidden">
                {/* Header */}
                <div className="p-6 pb-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0 pr-3">
                      <h3 className="font-semibold text-gray-900 text-base leading-tight mb-1 line-clamp-2" title={sanitizeName(it.name)}>
                        {sanitizeName(it.name)}
                      </h3>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 capitalize">
                          {it.registry}
                        </span>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <ScoreBadge id={it.id} initialScore={it.latest_score?.score_overall as any} />
                    </div>
                  </div>
                  
                  {/* Description */}
                  {it.description && (
                    <p className="text-sm text-gray-600 line-clamp-2 leading-relaxed mb-4">
                      {it.description}
                    </p>
                  )}
                </div>
                
                {/* Actions */}
                <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex gap-3">
                  <Link 
                    href={`/server/${it.id}`} 
                    className="flex-1 text-center px-3 py-2 bg-gray-100 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-200 hover:border-gray-400 transition-colors"
                  >
                    View Details
                  </Link>
                  <Link 
                    href={`/server/${it.id}/security`} 
                    className="flex-1 text-center px-3 py-2 bg-gray-100 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-200 hover:border-gray-400 transition-colors"
                  >
                    Security
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {/* Pagination */}
      {items.length > 0 && (
        <div className="flex items-center justify-between pt-8 border-t border-gray-200">
          <div className="flex items-center space-x-4">
            <button
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white"
              onClick={() => runSearch(q, Math.max(0, offset - limit))}
              disabled={offset === 0 || loading}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Previous
            </button>
            <button
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white"
              onClick={() => runSearch(q, offset + limit)}
              disabled={loading || (total !== null && offset + limit >= total)}
            >
              Next
              <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
          
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span className="font-medium">
              Page {Math.floor(offset / limit) + 1}{total ? ` of ${Math.max(1, Math.ceil(total / limit))}` : ''}
            </span>
            {total !== null && (
              <span className="text-gray-500">
                Showing {Math.min(offset + 1, total)} - {Math.min(offset + limit, total)} of {total.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}


