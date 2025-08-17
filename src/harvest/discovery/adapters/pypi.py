from __future__ import annotations

import asyncio
import re
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ...models import SourceHit
from ...util import load_config


_sem = asyncio.Semaphore(6)
HREF_PROJ = re.compile(r"/project/([A-Za-z0-9_.\-]+)/")


def _headers() -> dict:
    ua = load_config().get("crawl", {}).get("user_agent", "MCPHarvester/1.0")
    return {"User-Agent": ua}


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2.0))
async def _get_text(client: httpx.AsyncClient, url: str, **params) -> str:
    async with _sem:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.text


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2.0))
async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    async with _sem:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def search(terms: List[str], limit: int = 100) -> List[SourceHit]:
    # PyPI has no official search API; use HTML results conservatively
    q = "+".join(terms + ["modelcontextprotocol", "mcp"]).strip("+")
    url = f"https://pypi.org/search/?q={q}"
    items: List[SourceHit] = []
    async with httpx.AsyncClient(headers=_headers(), timeout=20.0, http2=True) as client:
        html = await _get_text(client, url)
        names = HREF_PROJ.findall(html)
        names = list(dict.fromkeys(names))[: min(limit, 40)]
        for name in names:
            try:
                meta = await _get_json(client, f"https://pypi.org/pypi/{name}/json")
            except Exception:
                continue
            info = meta.get("info", {})
            proj_urls = info.get("project_urls", {}) or {}
            repo = None
            # Prefer Source or Repository URLs pointing to GitHub
            for key in ["Source", "Repository", "Homepage", "Code"]:
                val = proj_urls.get(key)
                if val and "github.com" in val:
                    repo = val
                    break
            if not repo:
                continue
            items.append(SourceHit(source="pypi", url=repo, title=name, snippet=info.get("summary") or ""))
            if len(items) >= limit:
                break
    return items[:limit]

