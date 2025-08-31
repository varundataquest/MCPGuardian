import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8015'

async function fetchDetail(id: string) {
  const res = await fetch(`${API_BASE}/servers/${id}`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function ServerDetail({ params }: { params: { id: string } }) {
  const data = await fetchDetail(params.id)
  if (!data) {
    return <div className="text-sm text-gray-600">Not found.</div>
  }
  const { server } = data
  const meta = (server?.metadata_json || {}) as any
  const tags: string[] = (server?.tags || []) as string[]
  // Prefer extracted arrays; fallback to mcp.json content if present
  const mcp = (meta?.mcp_json || {}) as any
  // New derived fields
  const projectVisibility = (meta?.project_visibility as string) || (server?.repo_url ? 'open_source' : 'closed_source')
  const hosting = (meta?.hosting || {}) as any
  const connectivity = (meta?.connectivity || {}) as any
  const deployment = (meta?.deployment || {}) as any
  const tools: { name: string; description?: string }[] = Array.isArray(meta?.tools)
    ? (meta.tools as string[]).map((n: string) => ({ name: String(n) }))
    : Array.isArray(mcp?.tools)
      ? (mcp.tools as any[]).map((t) => ({ name: String(t?.name || ''), description: t?.description }))
      : []
  const prompts: { name: string; description?: string }[] = Array.isArray(meta?.prompts)
    ? (meta.prompts as string[]).map((n: string) => ({ name: String(n) }))
    : Array.isArray(mcp?.prompts)
      ? (mcp.prompts as any[]).map((p) => ({ name: String(p?.name || ''), description: p?.description }))
      : []
  const resources: { name: string; description?: string; uri?: string }[] = Array.isArray(meta?.resources)
    ? (meta.resources as string[]).map((n: string) => ({ name: String(n) }))
    : Array.isArray(mcp?.resources)
      ? (mcp.resources as any[]).map((r) => ({
          name: String(r?.name || r?.title || r?.id || r?.uri || ''),
          description: r?.description,
          uri: r?.uri,
        }))
      : []
  return (
    <div>
      <div className="text-sm mb-2"><Link href="/">← Back</Link></div>

      {/* Header */}
      <div className="mb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">{server.name}</h2>
            <div className="text-xs text-gray-500 mt-1">{server.registry}</div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <a href={server.homepage_url} className="px-3 py-1 rounded border hover:bg-gray-50" target="_blank">Homepage</a>
            {server.repo_url && (
              <a href={server.repo_url} className="px-3 py-1 rounded border hover:bg-gray-50" target="_blank">Repo</a>
            )}
            <Link href={`/server/${server.id}/security`} className="px-3 py-1 rounded border hover:bg-gray-50">Security</Link>
          </div>
        </div>

        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {tags.map((t, i) => (
              <span key={i} className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      {server.description && (
        <div className="bg-white border rounded p-4 mb-4">
          <div className="text-sm text-gray-700 whitespace-pre-wrap">{server.description}</div>
        </div>
      )}

      {/* Links */}
      {(meta?.mcp_json_url || mcp?.wellKnownUrl) && (
        <div className="text-sm text-gray-600 mb-4">
          MCP JSON:{' '}
          <a
            href={(meta?.mcp_json_url || mcp?.wellKnownUrl) as string}
            className="text-blue-600 underline"
            target="_blank"
          >
            {(meta?.mcp_json_url || mcp?.wellKnownUrl) as string}
          </a>
        </div>
      )}

      {/* Links, Tools, Prompts, Resources */}
      {/* Project / Hosting & Connectivity / Deployment */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Project</div>
          <div className="text-sm text-gray-700">
            <div><span className="text-gray-500">Visibility:</span> {projectVisibility === 'open_source' ? 'Open source' : 'Closed source'}</div>
            {meta?.github?.license && (
              <div><span className="text-gray-500">License:</span> {meta.github.license}</div>
            )}
          </div>
        </div>
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Hosting & Connectivity</div>
          <div className="text-sm text-gray-700 space-y-1">
            {hosting?.host_domain && <div><span className="text-gray-500">Host:</span> {hosting.host_domain}</div>}
            <div><span className="text-gray-500">Public MCP JSON:</span> {hosting?.public_mcp_json ? 'Yes' : 'No'}</div>
            {hosting?.mcp_json_url && (
              <div><a href={hosting.mcp_json_url} className="text-blue-700 underline" target="_blank">View .well-known/mcp.json</a></div>
            )}
            <div><span className="text-gray-500">HTTPS:</span> {hosting?.https ? 'Yes' : 'No'}</div>
            <div><span className="text-gray-500">HSTS:</span> {hosting?.hsts ? 'Yes' : 'No'}</div>
            <div><span className="text-gray-500">Security headers:</span> {hosting?.security_headers_good ? 'Present' : 'Limited/None'}</div>
            <div><span className="text-gray-500">Can connect now:</span> {connectivity?.publicly_connectable ? 'Yes (public MCP JSON found)' : 'Unknown / self-hosted'}</div>
          </div>
        </div>
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Deployment</div>
          <div className="text-sm text-gray-700 space-y-1">
            {Array.isArray(deployment?.hints) && deployment.hints.length > 0 ? (
              <div><span className="text-gray-500">Hints:</span> {deployment.hints.join(', ')}</div>
            ) : (
              <div className="text-gray-500">No hints detected.</div>
            )}
            {deployment?.readme_url && (
              <div><a href={deployment.readme_url} className="text-blue-700 underline" target="_blank">Setup instructions (README)</a></div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Links</div>
          <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
            <li>
              <a href={server.homepage_url} className="underline" target="_blank">Homepage</a>
            </li>
            {server.repo_url && (
              <li>
                <a href={server.repo_url} className="underline" target="_blank">Repository</a>
              </li>
            )}
            {(meta?.mcp_json_url || mcp?.wellKnownUrl) && (
              <li>
                <a href={(meta?.mcp_json_url || mcp?.wellKnownUrl) as string} className="underline" target="_blank">MCP JSON</a>
              </li>
            )}
          </ul>
        </div>
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Tools</div>
          {tools.length > 0 ? (
            <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
              {tools.map((t, i) => (
                <li key={i}>
                  <span className="font-medium">{t.name || '—'}</span>
                  {t.description ? <span className="text-gray-600"> — {t.description}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No tools listed.</div>
          )}
        </div>
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Prompts</div>
          {prompts.length > 0 ? (
            <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
              {prompts.map((p, i) => (
                <li key={i}>
                  <span className="font-medium">{p.name || '—'}</span>
                  {p.description ? <span className="text-gray-600"> — {p.description}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No prompts listed.</div>
          )}
        </div>
        <div className="bg-white border rounded p-4">
          <div className="font-medium mb-2">Resources</div>
          {resources.length > 0 ? (
            <ul className="list-disc pl-5 space-y-1 text-sm text-gray-700">
              {resources.map((r, i) => (
                <li key={i}>
                  <span className="font-medium">{r.name || '—'}</span>
                  {r.description ? <span className="text-gray-600"> — {r.description}</span> : null}
                  {r.uri ? (
                    <span> — <a href={r.uri} target="_blank" className="text-blue-700 underline">{r.uri}</a></span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">No resources listed.</div>
          )}
        </div>
      </div>

      {/* Security moved to dedicated page */}
    </div>
  )
}


