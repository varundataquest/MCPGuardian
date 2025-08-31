from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator, Dict, List, Optional, Callable, Awaitable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import re

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
    # Prefer heading or og:title; trim trailing descriptive separators
    for sel in ["h1", "h2", "meta[property='og:title']", "title"]:
        el = dsoup.select_one(sel)
        if not el:
            continue
        txt = el.get_text(strip=True) if hasattr(el, 'get_text') else (el.get('content') or '')
        if txt:
            txt = txt.replace("\n", " ").strip()
            for sep in [" — ", " – ", " - ", " | "]:
                if sep in txt:
                    txt = txt.split(sep, 1)[0].strip()
            return _clean_name(txt)
    return None


async def _crawl_with_browser(
    base_url: str,
    max_servers: int,
    registry_name: str = "registry",
    progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
) -> List[str]:
    """Use browser automation to click 'Load More' and collect all server links."""
    server_links = []
    
    async with async_playwright() as p:
        # Use headless Chrome
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to the servers page
            logger.info("Loading servers page...")
            await page.goto(base_url, wait_until="networkidle")
            
            click_count = 0
            prev_count = 0
            no_progress_count = 0
            
            while len(server_links) < max_servers:
                # Check for cancellation at start of each iteration
                try:
                    await asyncio.sleep(0)  # Allow cancellation to be processed
                except asyncio.CancelledError:
                    logger.info("Registry crawl cancelled by user")
                    raise
                # Extract current server links using Playwright locators (more reliable)
                server_locator = page.locator('a[href*="/mcp/servers/"]:not([href*="/tools/"])')
                current_links = await server_locator.evaluate_all('links => links.map(link => link.href)')
                
                server_links = list(set(current_links))  # Remove duplicates
                
                # Early exit if we've reached the target
                if len(server_links) >= max_servers:
                    logger.info(f"🎯 {registry_name}: Reached target of {max_servers} servers, stopping browser collection")
                    break
                
                logger.info(f"Found {len(server_links)} servers after {click_count} Load More clicks")
                
                if progress_cb:
                    try:
                        await progress_cb({"registry": registry_name, "click": click_count, "found": len(server_links)})
                    except Exception:
                        pass
                
                # Check for progress
                if len(server_links) == prev_count:
                    no_progress_count += 1
                    if no_progress_count >= 5:  # Increased tolerance
                        logger.info("No progress for 5 attempts, stopping")
                        break
                else:
                    no_progress_count = 0
                    prev_count = len(server_links)
                
                # Try multiple Load More button selectors (button text might vary)
                load_more_selectors = [
                    'button:has-text("Load More")',
                    'button:has-text("Show More")', 
                    'button:has-text("More")',
                    'button[class*="load"]:has-text("More")',
                    'button[class*="show"]:has-text("More")'
                ]
                
                button_found = False
                for selector in load_more_selectors:
                    load_more_locator = page.locator(selector)
                    if await load_more_locator.count() > 0:
                        is_visible = await load_more_locator.is_visible()
                        is_enabled = await load_more_locator.is_enabled()
                        
                        if is_visible and is_enabled:
                            logger.info(f"Clicking Load More button (attempt {click_count + 1}, selector: {selector})...")
                            await load_more_locator.click()
                            click_count += 1
                            button_found = True
                            
                            # Wait longer for content to load and for any JavaScript to settle
                            await page.wait_for_timeout(4000)  # Increased to 4 seconds
                            
                            # Also wait for network to be idle (in case of AJAX)
                            try:
                                await page.wait_for_load_state('networkidle', timeout=5000)
                            except:
                                pass  # Continue if timeout
                            break
                
                if not button_found:
                    # Try pagination "Next" links as fallback
                    logger.info("No Load More button found, trying Next pagination links...")
                    # More specific selectors for pagination (not server names containing "Next")
                    next_selectors = [
                        'nav a:has-text("Next")',
                        '[class*="pagination"] a:has-text("Next")', 
                        '[class*="pager"] a:has-text("Next")',
                        'a[href*="?page="]:has-text("Next")',
                        'a[href*="page="]:has-text("Next")',
                        'button[class*="next"]:has-text("Next")',
                        # Try numeric pagination like 1, 2, 3, 4...
                        'nav a:has-text("2")',
                        '[class*="pagination"] a:has-text("2")',
                        'a[href*="page"]:not([href*="/mcp/servers/"])',  # Page links but not server links
                    ]
                    
                    next_found = False
                    for selector in next_selectors:
                        next_locator = page.locator(selector)
                        if await next_locator.count() > 0:
                            is_visible = await next_locator.is_visible()
                            is_enabled = await next_locator.is_enabled()
                            
                            if is_visible and is_enabled:
                                logger.info(f"Clicking Next link (attempt {click_count + 1}, selector: {selector})...")
                                await next_locator.first.click()  # Use .first in case multiple elements
                                click_count += 1
                                next_found = True
                                
                                # Wait for navigation/content load
                                await page.wait_for_timeout(4000)
                                try:
                                    await page.wait_for_load_state('networkidle', timeout=5000)
                                except:
                                    pass
                                break
                    
                    if not next_found:
                        logger.info(f"No clickable Load More or Next links found after {click_count} clicks, stopping")
                        break
                
                # Stop if we've clicked too many times (safety) - increased limit for Next links
                if click_count >= 50:
                    logger.info("Reached maximum click limit (50), stopping")
                    break
            
        except asyncio.CancelledError:
            logger.info("Registry browser automation cancelled")
            raise
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
        finally:
            # Always close browser, even on cancellation
            try:
                await browser.close()
            except Exception:
                pass  # Ignore errors during cleanup
    
    logger.info(f"Browser crawl complete: found {len(server_links)} server links")
    return server_links


class GlamaRegistry(BaseRegistry):
    """Registry implementation for Glama.ai"""
    
    async def crawl(
        self,
        max_pages: int = 10,
        rate_limit_per_host: float = 2.0,
        user_agent: str = "AgentAgentGoBot/0.1",
        progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
        max_items: Optional[int] = None,
        persist_to_supabase: bool = False,
    ) -> List[Dict]:
        """Crawl glama.ai using browser automation to handle 'Load More' button.

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

        # Calculate max servers to collect - use max_items if provided, otherwise estimate from pages
        if max_items is not None:
            max_servers = max_items
        else:
            max_servers = max_pages * 20  # Estimate 20 servers per "page"

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=httpx.Timeout(30.0)) as client:
            robots = await fetch_robots_txt(base, client, per_host, user_agent=user_agent)
            allowed = is_path_allowed_by_robots(robots, user_agent, "/mcp/servers")
            if not allowed:
                logger.warning("robots.txt disallows crawling %s", base)
                return []

            # Use browser automation to get all server links
            logger.info(f"Starting browser crawl for up to {max_servers} servers...")
            server_links = await _crawl_with_browser(base, max_servers, self.registry_name, progress_cb)
            
            if not server_links:
                logger.warning("No server links found via browser automation")
                return []

            logger.info(f"Processing {len(server_links)} server detail pages...")
            
            # Process each server link to extract detailed information
            for i, server_url in enumerate(server_links):
                # Check for cancellation during server processing
                try:
                    await asyncio.sleep(0)  # Allow cancellation to be processed
                except asyncio.CancelledError:
                    logger.info(f"{self.registry_name} server processing cancelled by user")
                    raise
                    
                # Check both max_servers (from browser) and max_items (from user cap)
                if len(results) >= max_servers:
                    break
                # Check if we've reached the cap and need immediate DB write
                if max_items is not None and len(results) >= max_items:
                    if not cap_reached_and_persisted and persist_to_supabase:
                        # Immediate DB write when cap is reached
                        try:
                            from app.db.supabase_client import get_supabase_client
                            from app.db.repository import upsert_servers
                            sb = get_supabase_client()
                            await upsert_servers(sb, results)
                            logger.info(f"🎯💾 {self.registry_name}: Cap reached! Immediately persisted {len(results)} servers to database")
                            cap_reached_and_persisted = True
                            
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
                    
                    logger.info(f"🎯 {self.registry_name}: Reached max_items limit of {max_items}, stopping processing with {len(results)} servers")
                    break
                    
                try:
                    # Skip obvious category/tag pages that cause 500 errors
                    if "/categories/" in server_url or "/tags/" in server_url:
                        logger.debug(f"Skipping category/tag page: {server_url}")
                        continue
                        
                    await per_host.acquire(httpx.URL(server_url).host or "")
                    req = lambda u=server_url: client.build_request("GET", u)
                    resp = await exponential_backoff_request(client, req)
                    if resp.status_code != 200:
                        continue
                    
                    dsoup = BeautifulSoup(resp.text, "html.parser")
                    
                    # Extract name
                    name = _extract_name_from_detail(dsoup)
                    if not name:
                        # Fallback: extract from URL
                        parts = server_url.strip("/").split("/")
                        if len(parts) >= 2:
                            name = parts[-1].replace("-", " ").title()
                        else:
                            continue
                    
                    # Extract description
                    desc = None
                    desc_el = dsoup.select_one("meta[name='description']") or dsoup.find("p")
                    if desc_el:
                        desc = desc_el.get("content") if desc_el.name == "meta" else desc_el.get_text(strip=True)

                    homepage_url: Optional[str] = None
                    repo_url: Optional[str] = None
                    
                    # Heuristics: look for external links
                    for link in dsoup.select("a[href]"):
                        href = link.get("href")
                        if not href or not href.startswith("http"):
                            continue
                        if "github.com" in href and repo_url is None:
                            repo_url = href
                        elif homepage_url is None and not any(x in href for x in [self.config.url.split('//')[1].split('/')[0], "javascript:", "mailto:"]):
                            homepage_url = href

                    if not homepage_url:
                        # fallback to detail page URL
                        homepage_url = server_url

                    if homepage_url in seen_homepages:
                        continue
                    seen_homepages.add(homepage_url)

                    tags = [t.get_text(strip=True) for t in dsoup.select("a[href*='tag'], a[href*='categor']") if t] or []
                    item = {
                        "registry": self.registry_name,
                        "name": name,
                        "slug": _normalize_slug(name),
                        "homepage_url": homepage_url,
                        "repo_url": repo_url,
                        "description": desc,
                        "tags": tags,
                    }
                    results.append(item)
                    # Periodic persistence during crawl
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
                        # Immediate DB write on cap after append
                        if not cap_reached_and_persisted and persist_to_supabase:
                            try:
                                from app.db.supabase_client import get_supabase_client
                                from app.db.repository import upsert_servers
                                sb = get_supabase_client()
                                await upsert_servers(sb, results[last_persist_idx:len(results)] or results)
                                cap_reached_and_persisted = True
                                last_persist_idx = len(results)
                                logger.info(f"🎯💾 {self.registry_name}: Cap reached! Immediately persisted {len(results)} servers to database")
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
                        logger.info(f"{self.registry_name}: Reached max_items limit of {max_items}, stopping immediately with {len(results)} servers")
                        break
                    
                    # Progress callback every 5 servers processed (not just found)
                    if progress_cb and (i + 1) % 5 == 0:
                        try:
                            await progress_cb({
                                "registry": self.registry_name, 
                                "processed": i + 1, 
                                "total_links": len(server_links),
                                "found": len(results),
                                "phase": "processing_details"
                            })
                        except Exception:
                            pass
                        
                except Exception as e:
                    logger.debug(f"Error processing {server_url}: {e}")
                    continue

            logger.info(f"{self.registry_name} crawl complete: {len(results)} total servers collected")
            return results





