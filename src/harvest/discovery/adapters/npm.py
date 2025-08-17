from __future__ import annotations

import asyncio
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ...models import SourceHit
from ...util import load_config


_sem = asyncio.Semaphore(5)


def _headers() -> dict:
    ua = load_config().get("crawl", {}).get("user_agent", "MCPHarvester/1.0")
    return {"User-Agent": ua}


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2.0))
async def _get(client: httpx.AsyncClient, url: str, **params) -> dict:
    async with _sem:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


def _sanitize_repo(repo: str | None) -> str | None:
    if not repo:
        return None
    r = repo.strip()
    if r.startswith("git+"):
        r = r[4:]
    if r.startswith("git@github.com:"):
        path = r.split(":", 1)[1]
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"
    if r.startswith("git+ssh://git@github.com/"):
        path = r.split("github.com/", 1)[1]
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"
    if r.startswith("ssh://git@github.com/"):
        path = r.split("github.com/", 1)[1]
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"
    if r.startswith("git://github.com/"):
        path = r.split("github.com/", 1)[1]
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"
    if r.endswith(".git") and r.startswith("https://github.com/"):
        return r[:-4]
    return r if r.startswith("http://") or r.startswith("https://") else None


async def search(terms: List[str], limit: int = 100) -> List[SourceHit]:
    q = " ".join(terms + ["modelcontextprotocol", "mcp"]).strip()
    url = "https://registry.npmjs.org/-/v1/search"
    items: List[SourceHit] = []
    async with httpx.AsyncClient(headers=_headers(), timeout=20.0, http2=True) as client:
        try:
            data = await _get(client, url, text=q, size=min(limit, 50))
        except httpx.HTTPStatusError:
            # fallback without extra tokens which can cause 400s
            simple_q = " ".join(terms)
            try:
                data = await _get(client, url, text=simple_q, size=min(limit, 50))
            except Exception:
                return items
        for obj in data.get("objects", []):
            pkg = obj.get("package", {})
            repo_raw = (pkg.get("links", {}) or {}).get("repository")
            repo = _sanitize_repo(repo_raw)
            if not repo or "github.com" not in repo:
                continue
            title = pkg.get("name")
            desc = pkg.get("description") or ""
            items.append(SourceHit(source="npm", url=repo, title=title, snippet=desc))
            if len(items) >= limit:
                break
    return items[:limit]

