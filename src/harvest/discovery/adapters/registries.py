from __future__ import annotations

import asyncio
import re
from typing import List

import httpx
from ...models import SourceHit
from ...util import load_config


async def search(terms: List[str], limit: int = 100) -> List[SourceHit]:
    cfg = load_config()
    ua = cfg.get("crawl", {}).get("user_agent", "MCPHarvester/1.0")
    headers = {"User-Agent": ua}
    urls = [
        "https://mcpservers.org/",
        "https://raw.githubusercontent.com/modelcontextprotocol/servers/refs/heads/main/README.md",
        "https://mcp.so/",
    ]
    hits: List[SourceHit] = []
    gh_pat = re.compile(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    term_pat = re.compile("|".join(re.escape(t) for t in terms), re.I)
    async with httpx.AsyncClient(headers=headers, timeout=20.0, http2=True) as client:
        reqs = [client.get(u) for u in urls]
        resps = await asyncio.gather(*reqs, return_exceptions=True)
        for u, r in zip(urls, resps):
            if isinstance(r, Exception) or getattr(r, "status_code", 500) != 200:
                continue
            text = r.text
            for m in gh_pat.findall(text):
                # attach the page title when available
                title = m.split("github.com/")[-1]
                # Filter by term presence in page text to loosely match query
                if term_pat.search(text):
                    hits.append(SourceHit(source="registries", url=m, title=title))
                if len(hits) >= limit:
                    return hits[:limit]
    return hits[:limit]

