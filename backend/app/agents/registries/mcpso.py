from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Optional, Callable, Awaitable
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ...crew.utils import (
    PerHostRateLimiter,
    exponential_backoff_request,
    fetch_robots_txt,
    is_path_allowed_by_robots,
)
from .base import BaseRegistry


logger = logging.getLogger(__name__)


def _normalize_slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")


def _clean_name(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"\s+", " ", s)
    # Remove repeated leading character (e.g., 'GGitLab' -> 'GitLab')
    while len(s) >= 2 and s[0] == s[1]:
        s = s[1:]
    # Collapse duplicated first token with no delimiter (e.g., 'GitLabGitLab API' -> 'GitLab API')
    s = re.sub(r"^([A-Za-z][A-Za-z0-9\-]{2,})\1(\b|\s)", r"\\1\\2", s)
    # Collapse duplicated first token with space (e.g., 'GitLab GitLab API' -> 'GitLab API')
    s = re.sub(r"^([A-Za-z][A-Za-z0-9\-]{2,})\s+\1(\b|\s)", r"\\1\\2", s, flags=re.IGNORECASE)
    return s


def _extract_name_from_detail(dsoup: BeautifulSoup) -> Optional[str]:
    # Prefer prominent headings or og:title
    for sel in ["h1", "h2", "meta[property='og:title']", "title"]:
        el = dsoup.select_one(sel)
        if not el:
            continue
        txt = el.get_text(strip=True) if hasattr(el, 'get_text') else (el.get('content') or '')
        if txt:
            # Keep only the first line/chunk; many pages include summary after a separator
            txt = txt.replace("\n", " ").strip()
            for sep in [" — ", " – ", " - ", " | "]:
                if sep in txt:
                    txt = txt.split(sep, 1)[0].strip()
            return _clean_name(txt)
    return None


class McpsoRegistry(BaseRegistry):
    """Registry implementation for mcp.so"""
    
    async def crawl(
        self,
        max_pages: int = 10,
        rate_limit_per_host: float = 2.0,
        user_agent: str = "AgentAgentGoBot/0.1",
        progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
        max_items: Optional[int] = None,
        persist_to_supabase: bool = False,
    ) -> List[Dict]:
        """Crawl mcp.so registry pages with simple pagination.

        Returns a list of dicts: {name, slug, homepage_url, repo_url?, description?, tags?, registry}
        """
        base = self.base_url
        per_host = PerHostRateLimiter(rate_limit_per_host)
        headers = {"User-Agent": user_agent}
        results: List[Dict] = []
        seen_homepages = set()
        cap_reached_and_persisted = False  # Track if we've already persisted when cap reached
        # Periodic persistence controls
        batch_size = int(os.getenv("PERSIST_BATCH_SIZE", "100"))
        last_persist_idx = 0

        logger.info(f"{self.registry_name}: Starting crawl with max_pages={max_pages}, max_items={max_items}")
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(30.0)) as client:
            robots = await fetch_robots_txt(base, client, per_host, user_agent=user_agent)
            if not is_path_allowed_by_robots(robots, user_agent, "/servers"):
                logger.warning("robots.txt disallows crawling %s", base)
                return []

            page = 1
            total_found = 0
            while page <= max_pages:
                # Check if we've reached the max_items limit
                if max_items is not None and len(results) >= max_items:
                    logger.info(f"🎯 {self.registry_name}: Reached max_items limit of {max_items}, stopping at {len(results)} servers")
                    break
                # Check for cancellation
                try:
                    await asyncio.sleep(0)  # Allow cancellation to be processed
                except asyncio.CancelledError:
                    logger.info(f"{self.registry_name} crawl cancelled by user")
                    raise
                url = f"{base}?page={page}"
                await per_host.acquire(httpx.URL(base).host or "")
                resp = await exponential_backoff_request(client, lambda: client.build_request("GET", url))
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                # Be tolerant to both /server/ and /servers/ url shapes
                cards = soup.select("a[href*='/server/']")
                if not cards:
                    break
                for a in cards:
                    # Check for cancellation frequently during processing
                    try:
                        await asyncio.sleep(0)  # Allow cancellation to be processed
                    except asyncio.CancelledError:
                        logger.info(f"{self.registry_name} crawl cancelled during card processing")
                        raise
                        
                    detail_href = a.get("href") or ""
                    name = _clean_name(a.get_text(strip=True))
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
                    # Replace list name with detail-page title when available to avoid description run-on
                    detail_name = _extract_name_from_detail(dsoup)
                    if detail_name:
                        name = detail_name

                    homepage_url: Optional[str] = None
                    repo_url: Optional[str] = None
                    # Heuristic: prefer external links (non-mcp.so) for homepage, and first GitHub for repo
                    external_candidates: List[str] = []
                    repo_candidates: List[str] = []
                    for link in dsoup.select("a[href], link[href], meta[property='og:url']"):
                        href2 = link.get("href") or link.get("content") or ""
                        if not href2:
                            continue
                        if not href2.startswith("http"):
                            href2 = urljoin(detail_url, href2)
                        try:
                            u = httpx.URL(href2)
                            host = (u.host or "").lower()
                        except Exception:
                            continue
                        text = (link.get_text(strip=True) or "").lower()
                        if "github.com" in host:
                            # Prefer links whose text indicates repo
                            score = 2 if any(k in text for k in ["repo", "source", "github"]) else 1
                            # Avoid issue-only links as repo
                            if "/issues" in href2 or "/pull" in href2:
                                score -= 1
                            repo_candidates.append((score, href2.rstrip('/')))
                        # External homepage candidates (avoid mcp.so)
                        registry_domains = {self.config.url.replace("https://", "").replace("http://", "").split("/")[0]}
                        if host not in registry_domains and not href2.startswith("mailto:"):
                            score = 0
                            if any(k in text for k in ["home", "website", "docs", "documentation", "project"]):
                                score += 2
                            if any(k in host for k in ["github.io", "readthedocs", "vercel.app", "netlify.app"]):
                                score += 1
                            external_candidates.append((score, href2))

                    if repo_candidates:
                        repo_candidates.sort(reverse=True)
                        repo_url = repo_candidates[0][1]
                    if external_candidates:
                        external_candidates.sort(reverse=True)
                        homepage_url = external_candidates[0][1]
                        # If homepage is a social link (e.g., X/Twitter), fallback to repo homepage
                        try:
                            h = (httpx.URL(homepage_url).host or "").lower()
                        except Exception:
                            h = ""
                        if h in {"x.com", "twitter.com"} and repo_url:
                            homepage_url = repo_url

                    if not homepage_url:
                        # Fall back to repo as homepage if it's all we have
                        homepage_url = repo_url or detail_url
                    if homepage_url in seen_homepages:
                        continue
                    seen_homepages.add(homepage_url)

                    tags = [t.get_text(strip=True) for t in dsoup.select(".tag, a[href*='tag']")] or []
                    results.append(
                        {
                            "registry": self.registry_name,
                            "name": name,
                            "slug": _normalize_slug(name),
                            "homepage_url": homepage_url,
                            "repo_url": repo_url,
                            "description": desc,
                            "tags": tags,
                        }
                    )
                    # Periodic persistence of new items during crawl
                    if persist_to_supabase and batch_size > 0 and (len(results) - last_persist_idx) >= batch_size:
                        try:
                            from app.db.supabase_client import get_supabase_client
                            from app.db.repository import upsert_servers
                            sb = get_supabase_client()
                            new_batch = results[last_persist_idx:len(results)]
                            if new_batch:
                                await upsert_servers(sb, new_batch)
                                last_persist_idx = len(results)
                                logger.info(f"💾 {self.registry_name}: Periodic persist - saved {len(new_batch)} servers (total {len(results)})")
                                if progress_cb:
                                    try:
                                        await progress_cb({
                                            "registry": self.registry_name,
                                            "phase": "periodic_persist",
                                            "persisted": len(new_batch),
                                            "total": len(results)
                                        })
                                    except Exception:
                                        pass
                        except Exception as exc:
                            logger.warning(f"Periodic persist failed for {self.registry_name}: {exc}")
                    
                    # Check if we've reached the max_items limit after adding this server
                    if max_items is not None and len(results) >= max_items:
                        if not cap_reached_and_persisted and persist_to_supabase:
                            # Immediate DB write when cap is reached
                            try:
                                from app.db.supabase_client import get_supabase_client
                                from app.db.repository import upsert_servers
                                sb = get_supabase_client()
                                await upsert_servers(sb, results[last_persist_idx:len(results)] or results)
                                logger.info(f"🎯💾 {self.registry_name}: Cap reached! Immediately persisted {len(results)} servers to database")
                                cap_reached_and_persisted = True
                                last_persist_idx = len(results)
                                
                                # Send progress callback for immediate persist
                                if progress_cb:
                                    try:
                                        await progress_cb({
                                            "registry": self.registry_name,
                                            "cap_reached": True,
                                            "persisted": len(results),
                                            "message": f"🎯💾 Cap reached! Saved {len(results)} servers to database"
                                        })
                                    except Exception:
                                        pass
                            except Exception as exc:
                                logger.warning(f"Failed to persist {self.registry_name} servers on cap reached: {exc}")
                        
                        logger.info(f"🎯 {self.registry_name}: Reached max_items limit of {max_items}, stopping immediately with {len(results)} servers")
                        return results

                            # Simple numeric pagination - just increment page number and continue
                page += 1
                total_found = len(results)
                if progress_cb:
                    try:
                        await progress_cb({"registry": self.registry_name, "page": page, "found": total_found})
                    except Exception:
                        pass

            # After processing pages or reaching caps, return what we collected
            return results





