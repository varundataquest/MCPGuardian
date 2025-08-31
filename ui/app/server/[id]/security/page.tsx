import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8015'

async function fetchDetail(id: string) {
  const res = await fetch(`${API_BASE}/servers/${id}`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

function subBadgeClasses(pct: number) {
  if (pct < 40) return 'bg-red-100 text-red-700'
  if (pct <= 60) return 'bg-yellow-100 text-yellow-700'
  return 'bg-green-100 text-green-700'
}

function badgeClasses(v: number) {
  if (v > 75) return 'bg-green-100 text-green-700'
  if (v >= 70) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

export default async function SecurityPage({ params }: { params: { id: string } }) {
  const data = await fetchDetail(params.id)
  if (!data) {
    return <div className="text-sm text-gray-600">Not found.</div>
  }
  const { server, latest_score } = data
  const fallbackFor = (k: string) => {
    switch (k) {
      case 'runtime_capabilities':
        return 'No runtime evidence provided or detected (allowlists, auth, rate limits, timeouts).'
      case 'repo_hygiene':
        return 'No repository hygiene evidence provided or detected (license, SECURITY.md, CODEOWNERS).'
      case 'release_cadence':
        return 'No release activity evidence provided or detected.'
      case 'ci_presence':
        return 'No CI workflow evidence provided or detected.'
      case 'trust_signals':
        return 'No trust signals provided or detected (HSTS, security.txt).'
      case 'distribution_host':
        return 'No distribution evidence provided or detected (public .well-known/mcp.json, security headers).'
      default:
        return 'No evidence provided or detected.'
    }
  }
  return (
    <div>
      <div className="text-sm mb-2"><Link href={`/server/${server.id}`}>← Back to Details</Link></div>
      <h2 className="text-xl font-semibold mb-2">Security Overview</h2>
      <div className="text-sm text-gray-500 mb-4">{server.name}</div>
      {latest_score ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className={`rounded px-2 py-0.5 text-sm font-medium ${badgeClasses(Number(latest_score.score_overall))}`}>
              Score {Math.round(Number(latest_score.score_overall))}/100
            </span>
            <span className="text-xs text-gray-500">as of {new Date(latest_score.created_at).toLocaleString()}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries((latest_score.breakdown_json || {}) as Record<string, any>).map(([k, raw]) => {
              const weights = (latest_score.weights || {}) as Record<string, number>
              const val = Number(raw)
              const max = Number(weights[k]) || 100
              const pct = max > 0 ? Math.round((val / max) * 100) : 0
              return (
                <div key={k} className="bg-white border rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-sm font-medium">{k.replace(/_/g, ' ')}</div>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${subBadgeClasses(pct)}`}>{Math.round(val)}/{Math.round(max)}</span>
                  </div>
                  {/* raw only; no percentage */}
                  {/* Reasons */}
                  <div className="text-xs text-gray-700 space-y-1">
                    {Array.isArray((latest_score as any).details?.[k]) && (latest_score as any).details[k].length > 0 ? (
                      (latest_score as any).details[k].map((r: any, idx: number) => (
                        <div key={idx} className="flex items-start gap-2">
                          <span className={r.delta >= 0 ? 'text-green-700' : 'text-red-700'}>{r.delta >= 0 ? `+${r.delta}` : r.delta}</span>
                          <span>
                            {r.message}
                            {r.evidence ? (
                              <>
                                {' '}
                                <a href={String(r.evidence)} target="_blank" className="text-blue-700 underline">evidence</a>
                              </>
                            ) : null}
                          </span>
                        </div>
                      ))
                    ) : (
                      <div className="text-gray-500">{fallbackFor(k)}</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="text-sm text-gray-600">No score available.</div>
      )}
    </div>
  )
}


