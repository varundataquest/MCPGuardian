from __future__ import annotations

import asyncio
import os
from typing import Dict, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ...models import SourceHit
from ...util import load_config


_sem = asyncio.Semaphore(10)


def _headers() -> Dict[str, str]:
    cfg = load_config()
    ua = cfg.get("crawl", {}).get("user_agent", "MCPHarvester/1.0")
    headers = {"User-Agent": ua}
    token_env = cfg.get("apis", {}).get("github_token_env", "GITHUB_TOKEN")
    tok = os.environ.get(token_env)
    if tok:
        headers["Authorization"] = f"token {tok}"
    return headers


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2.0))
async def _get_json(client: httpx.AsyncClient, url: str, **params):
    async with _sem:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def search(terms: List[str], limit: int = 100) -> List[SourceHit]:
    q = " ".join(terms)
    items: List[SourceHit] = []
    params = {"q": f"{q} in:readme,description", "per_page": 50}
    async with httpx.AsyncClient(headers=_headers(), timeout=20.0, http2=True) as client:
        for page in (1, 2):
            data = await _get_json(client, "https://api.github.com/search/repositories", **params, page=page)
            for it in data.get("items", []):
                lic = (it.get("license") or {}).get("spdx_id") if it.get("license") else None
                items.append(
                    SourceHit(
                        source="github",
                        url=it.get("html_url"),
                        title=it.get("full_name"),
                        snippet=(it.get("description") or ""),
                        extra={
                            "stars": it.get("stargazers_count"),
                            "pushed_at": it.get("pushed_at"),
                            "archived": it.get("archived", False),
                            "license": lic,
                        },
                    )
                )
            if len(items) >= limit:
                break
    return items[:limit]

