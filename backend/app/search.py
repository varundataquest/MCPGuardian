from __future__ import annotations

import os
from dataclasses import dataclass
import json
import httpx
from typing import Dict, List, Optional, Tuple


@dataclass
class SearchFilters:
    registry_in: Optional[List[str]] = None
    tags_any: Optional[List[str]] = None
    sort: Optional[str] = None  # 'stars' | 'recent' | None


def simple_heuristic_nl_to_filters(query: str) -> SearchFilters:
    q = (query or "").lower()
    tags: List[str] = []
    registries: List[str] = []
    sort: Optional[str] = None

    if "official" in q:
        tags.append("Official")
    if "security" in q or "iam" in q:
        tags.append("Security")
    if "database" in q or "postgres" in q or "mongodb" in q:
        tags.append("Databases")
    if "web" in q and ("scrap" in q or "crawl" in q or "browser" in q):
        tags.append("Web Scraping")
    if "stars" in q:
        sort = "stars"
    if "recent" in q or "latest" in q or "new" in q:
        sort = "recent"
    if "glama" in q:
        registries.append("glama")
    if "mcp.so" in q or "mcpso" in q:
        registries.append("mcpso")

    return SearchFilters(
        registry_in=registries or None,
        tags_any=tags or None,
        sort=sort,
    )


def nl_to_filters(query: str) -> Tuple[SearchFilters, Optional[str]]:
    """Translate NL to filters. Returns (filters, residual_free_text).

    Order:
    1) If GEMINI_API_KEY is present, attempt an LLM translation (bounded, JSON-only)
    2) Fallback to deterministic heuristic
    """
    # Try Gemini first if configured
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and (query or "").strip():
        try:
            prompt = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    "You are a strict translator that converts natural-language MCP search queries into a JSON object with this exact schema:\n"
                                    "{\n  \"registry_in\": string[] | null,\n  \"tags_any\": string[] | null,\n  \"sort\": 'rank'|'stars'|'recent'|null,\n  \"residual\": string | null\n}\n"
                                    "Rules: respond with JSON only; no prose.\n"
                                    "Normalize registries to ['glama','mcpso'] if mentioned.\n"
                                    "Extract topical tags (e.g., 'Official','Security','Databases','Web Scraping') if present.\n"
                                    "Sort: 'stars' if stars requested; 'recent' for freshness; else null.\n"
                                    f"Query: {query}"
                                )
                            }
                        ]
                    }
                ]
            }
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-1.5-flash:generateContent?key=" + gemini_key
            )
            with httpx.Client(timeout=httpx.Timeout(12)) as client:
                r = client.post(url, json=prompt)
            if r.status_code == 200:
                data = r.json()
                text = (
                    ((data.get("candidates") or [{}])[0]
                     .get("content", {})
                     .get("parts", [{}])[0]
                     .get("text", ""))
                )
                # Extract JSON block
                json_str = text.strip()
                parsed = json.loads(json_str)
                f = SearchFilters(
                    registry_in=parsed.get("registry_in") or None,
                    tags_any=parsed.get("tags_any") or None,
                    sort=parsed.get("sort") or None,
                )
                residual = (parsed.get("residual") or None)
                return f, residual
        except Exception:
            # fall back to heuristic
            pass

    filters = simple_heuristic_nl_to_filters(query)
    # Residual text after removing known keywords
    residual = query
    for w in [
        "official",
        "security",
        "database",
        "postgres",
        "mongodb",
        "web",
        "scrap",
        "crawl",
        "browser",
        "stars",
        "recent",
        "latest",
        "new",
        "glama",
        "mcp.so",
        "mcpso",
    ]:
        residual = residual.replace(w, " ")
    residual = " ".join(residual.split())
    return filters, (residual or None)


def build_search_sql(
    q: Optional[str],
    filters: Optional[SearchFilters] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[str, Dict[str, object]]:
    """Builds a parameterized Postgres SQL query for searching servers.

    - Uses a tsvector column `search_tsv` over name, description, tags
    - Supports filters: registry_in, tags_any
    - Sorting: stars|recent|rank(default)
    - Clamps limit/offset
    """
    filters = filters or SearchFilters()

    # Clamp
    limit = max(1, min(limit, 100))
    offset = max(0, min(offset, 10_000))

    where: List[str] = []
    params: Dict[str, object] = {}

    tsquery_expr = None
    if q:
        tsquery_expr = "websearch_to_tsquery('english', %(q)s)"
        where.append("search_tsv @@ " + tsquery_expr)
        params["q"] = q

    if filters.registry_in:
        where.append("registry = ANY(%(registry_in)s)")
        params["registry_in"] = filters.registry_in

    if filters.tags_any:
        # tags is text[]; use overlap (&&)
        where.append("tags && %(tags_any)s")
        params["tags_any"] = filters.tags_any

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    # Sorting
    order_sql = ""
    if filters.sort == "stars":
        order_sql = " ORDER BY github_stars DESC NULLS LAST, updated_at DESC NULLS LAST"
    elif filters.sort == "recent":
        order_sql = " ORDER BY updated_at DESC NULLS LAST"
    else:
        if q:
            order_sql = " ORDER BY ts_rank(search_tsv, " + tsquery_expr + ") DESC, updated_at DESC NULLS LAST"
        else:
            order_sql = " ORDER BY updated_at DESC NULLS LAST"

    sql = (
        "SELECT id, registry, name, slug, homepage_url, repo_url, description, tags, github_stars, updated_at "
        "FROM servers" + where_sql + order_sql + " LIMIT %(limit)s OFFSET %(offset)s"
    )
    params["limit"] = limit
    params["offset"] = offset
    return sql, params


