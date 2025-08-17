from __future__ import annotations

import asyncio
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ...models import SourceHit
from ...util import load_config


_sem = asyncio.Semaphore(4)


def _headers() -> dict:
    ua = load_config().get("crawl", {}).get("user_agent", "MCPHarvester/1.0")
    return {"User-Agent": ua}


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2.0))
async def _get(client: httpx.AsyncClient, url: str, **params) -> dict:
    async with _sem:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def search(terms: List[str], limit: int = 100) -> List[SourceHit]:
    q = " ".join(terms + ["mcp", "modelcontextprotocol"]).strip()
    base = "https://hub.docker.com/api/content/v1/products/search"
    items: List[SourceHit] = []
    async with httpx.AsyncClient(headers=_headers(), timeout=20.0, http2=True) as client:
        data = await _get(client, base, q=q, type="image", source="community", page_size=min(limit, 50))
        for it in data.get("summaries", []):
            # Some summaries include 'source_repository' linking to GitHub
            src = it.get("source_repository") or it.get("source_url") or ""
            if src and "github.com" in src:
                items.append(SourceHit(source="dockerhub", url=src, title=it.get("name"), snippet=it.get("short_description") or ""))
                if len(items) >= limit:
                    break
    return items[:limit]

