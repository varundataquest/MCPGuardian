# MCP Guardian Architecture

MCP Guardian discovers Model Context Protocol (MCP) servers from public registries, enriches their metadata, computes security-centric scores (metadata-only, no cloning), stores results at scale in Supabase/Postgres, and exposes REST APIs and a Next.js UI. Orchestration uses CrewAI with deterministic fallbacks for CI.

## Components

- Registries Crawlers: connectors for `glama.ai` and `mcp.so` with pagination/"load more", respectful `robots.txt`, per-host rate limits, and backoff on 429/5xx. Deduplicate by `homepage_url` and normalized `slug`.
- Enrichment: HTML parsing, resilient selectors, discovery of `.well-known/mcp.json`, extraction of description/tags/tools/prompts, and optional GitHub repository metadata.
- Security Scoring: pure-metadata rubric defined in `app/security/rubric.yaml`, producing a normalized 0–100 score with a transparent breakdown.
- Storage: Supabase Postgres with tables for servers and scores, plus FTS `tsvector` + GIN for fast search across `name`, `description`, and `tags`.
- API: FastAPI service for list/detail/search and admin controls, including an SSE endpoint for live crawl progress.
- Orchestration: CrewAI Agents for crawling, enrichment, and scoring with bounded concurrency; agents call local Python tools.
- UI: Next.js App Router + Tailwind. Admin uses EventSource to consume backend SSE progress.

## High-level Data Flow

```mermaid
flowchart TB
    subgraph Registries
        gl[glama.ai]
        mcpso[mcp.so]
        pulsemcp[pulsemcp.com]
    end

    crawl[Crawler Agents\n(robots.txt + rate limiting)]
    enrich[Enrichment\n(HTML + mcp.json + GitHub)]
    score[Security Scoring\n(rubric.yaml → 0–100)]
    store[(Supabase Postgres)]
    api[FastAPI REST API\n/servers, /search, /admin]
    ui[Next.js App Router UI]
    sse[(SSE Progress)]
    openai[(OpenAI NL→filters)\noptional]
    github[(GitHub API)\noptional]

    gl --> crawl
    mcpso --> crawl
    %% pulsemcp removed

    crawl -->|raw items| dedup[Deduplicate by homepage_url/slug]
    dedup --> enrich
    enrich -->|metadata| score
    score -->|breakdown + overall| store
    store <--> api
    api --> ui
    api -.-> sse -.-> ui
    openai -. structured query .-> api
    github -. repo metadata .-> enrich
```

## Sequence Overview

1. Crawl registries (bounded concurrency), respecting `robots.txt`; handle pagination and 429/5xx with exponential backoff.
2. Deduplicate candidates by `homepage_url` and normalized `slug`.
3. Enrich each result by scraping the registry page and linked homepage, discovering `.well-known/mcp.json` when available, and optionally merging GitHub repo metadata (topics, license, stars, forks, issues, last push).
4. Score using the YAML rubric (no code execution or repo clone) to compute a stable 0–100 security score and a detailed breakdown.
5. Store servers and the latest score in Supabase/Postgres, maintaining indexes for pagination and search. A `tsvector` column and GIN index power FTS.
6. Expose REST APIs for list/detail/search and admin control. The admin SSE endpoint streams live progress; the UI consumes this via `EventSource`.

## Storage Sketch

- `servers` (id, registry, name, slug, homepage_url, repo_url, description, tags[], metadata_json, created_at, updated_at)
- `server_scores` (id, server_id, score_overall, breakdown_json, created_at)
- FTS: `servers.search_tsv` generated from name, description, and tags; GIN index; trigger to keep fresh.

## Operational Notes

- Secrets are provided via environment variables only. The backend never receives secrets from the UI.
- Rate limit knobs and pagination limits are configurable, with sensible clamps for safety.
- Deterministic fallbacks ensure CI can run without external APIs. When configured, OpenAI and GitHub enrich functionality but are not required.

## Acceptance criteria

- Backend boots via `PYTHONPATH=backend uvicorn app.main:app` and Docker (`docker compose up --build`).
- Crawlers: glama.ai and mcp.so paginate correctly. Per-host rate limiting and exponential backoff on 429/5xx.
- Enrichment extracts description, tags, discovers `.well-known/mcp.json`; GitHub metadata merged when a GitHub repo exists.
- Scoring returns overall 0–100 and a rubric-aligned breakdown; runtime risk uses heuristic penalties/rewards; no code execution.
- Supabase schema, triggers, indexes, and RPCs (`search_servers`, `search_servers_count`) applied and queries run.
- API: `/servers`, `/servers/{id}`, `/servers/{id}/score`, `/search`, admin SSE endpoints work; inputs clamped; `X-Total-Count` set when applicable.
- UI: Home search shows servers with Details/Security actions; card shows color-coded score badge; Security page shows pretty breakdown with colored pct and x/100; Admin page streams crawl progress.
- Tests: `pytest` passes (search heuristics/SQL clamp, API basic with stubbed client, scoring smoke).

## Constraints & quality bar

- Security first: respect `robots.txt`; no cloning or executing third-party code; metadata-only scoring; sanitize/validate inputs; CORS configured.
- Deterministic CI: all heuristics have offline paths; GitHub/OpenAI optional.
- Performance: bounded concurrency for crawling/enrichment/scoring; per-host rate limits; pagination and clamped limits (max 100); FTS via `tsvector` + GIN.
- Reliability: retries with exponential backoff; graceful fallbacks (RPC to direct table queries); defensive parsing of HTML/JSON; typed, readable code.
- Observability: SSE progress with heartbeats; clear error messages in API responses; minimal but meaningful logs.
- Maintainability: clean module boundaries (crawlers, tools, scoring, db, api, ui); readable code; small pure functions; no deep nesting; avoid inline comments.
- Deployability: Dockerfiles for backend/UI; `docker-compose.yml` for local stack; devcontainer config; Render deployment config.
