## mcp-registry-harvester

Harvest multiple MCP registries into a canonical CSV and provide a CLI/API for search, explanation, and clustering.

### Quickstart

1. Install with Poetry and activate the env:

```
poetry install
poetry run mcp-harvest --help
```

2. Configure environment (optional keys improve coverage):

```
cp .env.example .env
```

3. Run a crawl (deterministic sources only):

```
poetry run mcp-harvest crawl --include docker,mcp-get
```

### Data schema (servers.csv)

Canonical columns in `CSV_COLUMNS`:

```
registry, server_id, display_name, description, runtime, install, source_repo, homepage,
license, maintainer, auth_required, env_vars, tools, transports, registries_seen_in,
last_seen_iso, first_seen_iso, fingerprint_sha256, reputation_score, tags, notes
```

### Crawlers

- smithery: API/CLI if `SMITHERY_API_KEY` set; otherwise fixtures-only
- opentools: fixtures-only by default (HTML/API optional)
- docker: reads metadata fixtures under `fixtures/docker/servers/*.json`
- mcp-get: reads package fixtures under `fixtures/mcp-get/packages/*.json`
- mcp-servers: reads fixture JSON `fixtures/mcp-servers/servers.json`
- mastra-index: refreshes seed registry links from fixtures

Use `--fixtures-dir` with `mcp-harvest crawl` for deterministic runs.

### Query examples

```
poetry run mcp-harvest query "python gmail" --top 5
poetry run mcp-harvest explain docker:some-server
poetry run mcp-harvest clusters --plot data/clusters.png
```

### Env vars

- `SMITHERY_API_KEY` (optional)
- `OPENTOOLS_API_KEY` (optional)
- `GITHUB_TOKEN` (optional, improves reputation)
- `USER_AGENT` (override)
- `CRAWL_INCLUDE`, `CRAWL_EXCLUDE` (optional)



