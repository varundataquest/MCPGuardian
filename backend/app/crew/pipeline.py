from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from app.agents.registries.factory import RegistryFactory
from app.config.registry_config import registry_manager
from app.crew.enrichment import enrich_server_candidate
from app.security.scoring_agent import score_enriched_server
from app.db.supabase_client import get_supabase_client, SupabaseNotConfigured
from app.db.repository import upsert_servers, insert_scores


logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    enabled_registries: Optional[List[str]] = None  
    max_pages_per_registry: Optional[Dict[str, int]] = None  
    max_items_per_registry: Optional[Dict[str, Optional[int]]] = None  
    rate_limit_per_host: float = 2.0
    user_agent: str = "GenericBot/1.0"
    
    def __post_init__(self):
        if self.enabled_registries is None:
            enabled_registries = registry_manager.get_enabled_registries()
            self.enabled_registries = [f"registry_{i}" for i, _ in enumerate(enabled_registries, 1)]
        
        if self.max_pages_per_registry is None:
            default_pages = int(os.getenv("DEFAULT_MAX_PAGES", "2"))
            self.max_pages_per_registry = {r: default_pages for r in self.enabled_registries}
                
        if self.max_items_per_registry is None:
            self.max_items_per_registry = {r: None for r in self.enabled_registries}


@dataclass
class ConcurrencyConfig:
    crawl_concurrency: int = 6
    enrich_concurrency: int = 8
    score_concurrency: int = 12


async def _bounded_map(
    items: Sequence,
    worker: callable,
    concurrency: int,
    desc: str,
) -> List:
    sem = asyncio.Semaphore(concurrency)
    results: List = []

    async def run_one(idx: int, item):
        async with sem:
            try:
                val = await worker(item)
                return idx, val, None
            except Exception as exc:
                logger.warning("%s worker failed: %s", desc, exc)
                return idx, None, exc

    tasks = [asyncio.create_task(run_one(i, it)) for i, it in enumerate(items)]
    for fut in asyncio.as_completed(tasks):
        i, val, exc = await fut
        if exc is None:
            results.append(val)
    return results


class CrawlerAgent:
    def __init__(self, cfg: CrawlConfig, conc: ConcurrencyConfig):
        self.cfg = cfg
        self.conc = conc

    async def run(self, progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None, persist_to_supabase: bool = False) -> List[Dict]:
        # jobs: (display_registry_name, max_items_limit, coroutine_factory)
        jobs: List[Tuple[str, Optional[int], Callable[[], Awaitable[List[Dict]]]]] = []
        
        enabled_registries = registry_manager.get_enabled_registries()
        for i, registry_config in enumerate(enabled_registries, 1):
            registry_key = f"registry_{i}"
            if registry_key in self.cfg.enabled_registries:
                max_pages = self.cfg.max_pages_per_registry.get(registry_key, 2)
                max_items = self.cfg.max_items_per_registry.get(registry_key)
                
                registry_instance = RegistryFactory.create_registry(registry_config)
                
                jobs.append((
                    registry_config.name,
                    max_items,
                    lambda r=registry_instance, mp=max_pages, mi=max_items, persist=persist_to_supabase: r.crawl(
                        mp, self.cfg.rate_limit_per_host, self.cfg.user_agent, progress_cb, mi, persist
                    ),
                ))

        sem = asyncio.Semaphore(self.conc.crawl_concurrency)

        async def run_job(job: Tuple[str, Optional[int], Callable[[], Awaitable[List[Dict]]]]):
            registry, limit, job_callable = job
            async with sem:
                out = await job_callable()
                # Server-side guardrail: enforce max_items cap even if crawler over-collects
                if isinstance(limit, int) and limit is not None:
                    try:
                        if len(out) > int(limit):
                            out = out[: int(limit)]
                    except Exception:
                        pass
                return registry, out

        tasks = [asyncio.create_task(run_job(j)) for j in jobs]
        # Dynamic results dictionary based on enabled registries
        results_by_registry: Dict[str, List[Dict]] = {job[0]: [] for job in jobs}
        for fut in asyncio.as_completed(tasks):
            try:
                # Check for cancellation while waiting for crawler results
                try:
                    await asyncio.sleep(0)  # Allow cancellation to be processed
                except asyncio.CancelledError:
                    logger.info("Crawler coordination cancelled")
                    # Cancel any remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    raise
                    
                reg, part = await fut
                logger.info(f"🏁 Registry {reg} TASK COMPLETED with {len(part)} servers")
                if progress_cb:
                    try:
                        await progress_cb({"phase": "crawl", "registry": reg, "found": len(part)})
                    except Exception:
                        pass
                results_by_registry.setdefault(reg, []).extend(part)
                
                # Immediate DB write when registry completes (if persist enabled)
                if persist_to_supabase and part:
                    try:
                        from app.db.supabase_client import get_supabase_client
                        from app.db.repository import upsert_servers
                        sb = get_supabase_client()
                        await upsert_servers(sb, part)
                        logger.info(f"✅ Persisted {len(part)} servers from {reg} to database")
                        if progress_cb:
                            try:
                                await progress_cb({
                                    "crawl_step": {
                                        "phase": "immediate_persist", 
                                        "registry": reg,
                                        "persisted_count": len(part),
                                        "message": f"✅ Saved {len(part)} servers from {reg} to database"
                                    }
                                })
                            except Exception:
                                pass
                    except Exception as exc:
                        logger.warning(f"Failed to persist {reg} servers immediately: {exc}")
                        if progress_cb:
                            try:
                                await progress_cb({
                                    "crawl_step": {
                                        "phase": "persist_error",
                                        "registry": reg, 
                                        "message": f"⚠️ Failed to save {reg} servers: {exc}"
                                    }
                                })
                            except Exception:
                                pass
            except Exception as exc:
                logger.warning("crawler job failed: %s", exc)

        # Note: Per-registry limits are now handled during crawling, not post-processing
        # This ensures crawlers stop immediately when limits are reached instead of 
        # continuing to crawl and then truncating results

        # Deduplicate by homepage_url across combined list
        seen = set()
        deduped: List[Dict] = []
        combined: List[Dict] = []
        for registry_results in results_by_registry.values():
            combined.extend(registry_results)
        for it in combined:
            home = it.get("homepage_url")
            if not home or home in seen:
                continue
            seen.add(home)
            deduped.append(it)
        return deduped


class EnrichmentAgent:
    def __init__(self, conc: ConcurrencyConfig):
        self.conc = conc

    async def run(self, items: List[Dict]) -> List[Dict]:
        async def worker(item: Dict) -> Dict:
            return await enrich_server_candidate(item)

        return await _bounded_map(items, worker, self.conc.enrich_concurrency, "enrich")


class SecurityScorerAgent:
    def __init__(self, conc: ConcurrencyConfig):
        self.conc = conc

    async def run(self, items: List[Dict]) -> List[Tuple[Dict, Dict]]:
        async def worker(item: Dict) -> Tuple[Dict, Dict]:
            score = await score_enriched_server(item)
            return item, score

        return await _bounded_map(items, worker, self.conc.score_concurrency, "score")


async def run_pipeline(
    crawl_cfg: Optional[CrawlConfig] = None,
    conc_cfg: Optional[ConcurrencyConfig] = None,
    persist_to_supabase: bool = False,
    progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
) -> Dict[str, object]:
    crawl_cfg = crawl_cfg or CrawlConfig()
    conc_cfg = conc_cfg or ConcurrencyConfig()

    crawler = CrawlerAgent(crawl_cfg, conc_cfg)
    enricher = EnrichmentAgent(conc_cfg)
    scorer = SecurityScorerAgent(conc_cfg)

    discovered = await crawler.run(progress_cb=progress_cb, persist_to_supabase=persist_to_supabase)
    
    # Notify completion of crawl phase
    if progress_cb:
        try:
            await progress_cb({"phase": "crawl_complete", "discovered_count": len(discovered)})
        except Exception:
            pass
    
    # Check for cancellation before enrichment  
    try:
        await asyncio.sleep(0)
    except asyncio.CancelledError:
        logger.info("Pipeline cancelled before enrichment phase")
        raise
        
    # Notify start of enrichment phase
    if progress_cb:
        try:
            await progress_cb({"phase": "enrichment_started", "total_items": len(discovered)})
        except Exception:
            pass
        
    enriched = await enricher.run(discovered)

    # Incremental persistence: write every N, and at end
    batch_size = int(os.getenv("PERSIST_BATCH_SIZE", "100"))
    batches: List[List[Dict]] = []
    if persist_to_supabase and enriched:
        for i in range(0, len(enriched), max(1, batch_size)):
            batches.append(enriched[i : i + batch_size])
    
    # Check for cancellation before scoring
    try:
        await asyncio.sleep(0) 
    except asyncio.CancelledError:
        logger.info("Pipeline cancelled before scoring phase")
        raise
        
    # Notify start of scoring phase
    if progress_cb:
        try:
            await progress_cb({"phase": "scoring_started", "total_items": len(enriched)})
        except Exception:
            pass
        
    scored = await scorer.run(enriched)

    persisted = False
    if persist_to_supabase:
        # Notify start of database write phase
        if progress_cb:
            try:
                await progress_cb({"phase": "database_write_started", "total_items": len(scored)})
            except Exception:
                pass
        try:
            sb = get_supabase_client()
            # Upsert servers in batches first to ensure IDs exist, then insert all scores once
            if batches:
                persisted_count = 0
                for bstart, batch in enumerate(batches, 1):
                    await upsert_servers(sb, batch)
                    persisted_count += len(batch)
                    if progress_cb:
                        try:
                            await progress_cb({
                                "phase": "database_write_progress",
                                "persisted": persisted_count,
                                "batch": bstart,
                                "batch_size": len(batch),
                            })
                        except Exception:
                            pass
                # After all upserts, insert all scores in one go
                items_with_scores = [{"server": item, "score": score} for item, score in scored]
                await insert_scores(sb, items_with_scores)
            else:
                # Fallback single-shot persistence
                await upsert_servers(sb, enriched)
                items_with_scores = [{"server": item, "score": score} for item, score in scored]
                await insert_scores(sb, items_with_scores)
            persisted = True
            
            # Notify successful database write
            if progress_cb:
                try:
                    await progress_cb({
                        "phase": "database_write_complete", 
                        "persisted_servers": len(enriched),
                        "persisted_scores": len(scored)
                    })
                except Exception:
                    pass
        except SupabaseNotConfigured:
            logger.warning("Supabase not configured; skipping persistence")
        except Exception as exc:
            logger.warning("Persistence failed: %s", exc)

    # Notify pipeline completion
    if progress_cb:
        try:
            await progress_cb({
                "phase": "pipeline_complete", 
                "discovered": len(discovered),
                "enriched": len(enriched), 
                "scored": len(scored),
                "persisted": persisted
            })
        except Exception:
            pass

    return {
        "discovered_count": len(discovered),
        "enriched_count": len(enriched),
        "scored_count": len(scored),
        "samples": scored[:3],
        "persisted": persisted,
    }


