from __future__ import annotations

import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ...crew.utils import (
    PerHostRateLimiter,
    exponential_backoff_request,
    fetch_robots_txt,
    is_path_allowed_by_robots,
)


logger = logging.getLogger(__name__)


def _normalize_slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")


async def crawl_pulsemcp(
    max_pages: int = 10,
    rate_limit_per_host: float = 2.0,
    user_agent: str = "MCPGuardianBot/0.1",
) -> List[Dict]:
    """Crawl pulsemcp.com registry pages.

    Returns a list of dicts: {name, slug, homepage_url, repo_url?, description?, tags?, registry}
    """
    base = "https://pulsemcp.com/servers"
    per_host = PerHostRateLimiter(rate_limit_per_host)
    headers = {"User-Agent": user_agent}
    results: List[Dict] = []
    seen_homepages = set()

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(30.0)) as client:
        robots = await fetch_robots_txt(base, client, per_host, user_agent=user_agent)
        if not is_path_allowed_by_robots(robots, user_agent, "/servers"):
            logger.warning("robots.txt disallows crawling %s", base)
            return []

        page = 1
        while page <= max_pages:
            url = f"{base}?page={page}"
            await per_host.acquire(httpx.URL(base).host or "")
            resp = await exponential_backoff_request(client, lambda: client.build_request("GET", url))
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("a[href^='/server/']")
            if not cards:
                break
            for a in cards:
                detail_href = a.get("href") or ""
                name = a.get_text(strip=True)
                if not detail_href or not name:
                    continue
                detail_url = urljoin(base, detail_href)
                await per_host.acquire(httpx.URL(detail_url).host or "")
                dresp = await exponential_backoff_request(client, lambda u=detail_url: client.build_request("GET", u))
                if dresp.status_code != 200:
                    continue
                dsoup = BeautifulSoup(dresp.text, "html.parser")
                desc = None
                desc_el = dsoup.select_one("meta[name='description']") or dsoup.find("p")
                if desc_el:
                    desc = desc_el.get("content") if desc_el.name == "meta" else desc_el.get_text(strip=True)

                homepage_url: Optional[str] = None
                repo_url: Optional[str] = None
                for link in dsoup.select("a[href]"):
                    href2 = link.get("href")
                    if not href2:
                        continue
                    if href2.startswith("http"):
                        if "github.com" in href2 and repo_url is None:
                            repo_url = href2
                        elif homepage_url is None:
                            homepage_url = href2

                if not homepage_url:
                    homepage_url = detail_url
                if homepage_url in seen_homepages:
                    continue
                seen_homepages.add(homepage_url)

                tags = [t.get_text(strip=True) for t in dsoup.select(".tag, a[href*='tag']")] or []
                results.append(
                    {
                        "registry": "pulsemcp",
                        "name": name,
                        "slug": _normalize_slug(name),
                        "homepage_url": homepage_url,
                        "repo_url": repo_url,
                        "description": desc,
                        "tags": tags,
                    }
                )

            next_link = soup.find("a", string=lambda s: isinstance(s, str) and "next" in s.lower())
            if not next_link:
                break
            page += 1

    return results


