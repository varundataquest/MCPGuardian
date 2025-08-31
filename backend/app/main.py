from __future__ import annotations

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not installed

import asyncio
import json
import time
import uuid
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Response, Query, Header, Depends
import re
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.crew.pipeline import run_pipeline, CrawlConfig, ConcurrencyConfig
from app.crew.backfill import run_backfill, BackfillConfig
from app.search import nl_to_filters, build_search_sql
from app.llm.gemini import get_call_stats
from app.crew.utils import get_http_error_stats
from app.security.scoring_agent import get_rubric_weights, score_enriched_server
from app.db.supabase_client import get_supabase_client, SupabaseNotConfigured
from app.services.progress import ProgressBroker, CrawlController, ProgressEvent
from app.security.scoring_agent import get_rubric_weights


# Load env from backend/.env
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(_ENV_PATH)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MCPGuardian Backend"}
broker = ProgressBroker()
controller = CrawlController(broker)
backfill_controller = CrawlController(broker)


def require_admin_token(x_admin_token: str = Header(alias="X-Admin-Token")):
    """Validate admin token for protected endpoints"""
    expected_token = os.getenv("ADMIN_ACCESS_TOKEN")
    
    if not expected_token:
        raise HTTPException(
            status_code=500, 
            detail="Admin access token not configured on server"
        )
    
    if x_admin_token != expected_token:
        raise HTTPException(
            status_code=403, 
            detail="Invalid or missing admin token"
        )
    
    return True


def require_admin_token_flexible(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    token: Optional[str] = Query(default=None),
):
    """Validate admin token from header or query parameter for SSE compatibility.

    EventSource cannot set custom headers, so we allow `?token=...` as a fallback
    specifically for streaming endpoints.
    """
    expected_token = os.getenv("ADMIN_ACCESS_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="Admin access token not configured on server",
        )

    provided = x_admin_token or token
    if provided != expected_token:
        raise HTTPException(status_code=403, detail="Invalid or missing admin token")

    return True


def _sanitize_name(raw: str) -> str:
    s = str(raw or "").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return s
    # Cut on common separators that introduce descriptions/taglines
    for sep in [" — ", " – ", " - ", " | ", ": "]:
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    # Keep up to "MCP Server" if early in the string
    m = re.search(r"^(.*?\bMCP\s*Server)\b", s, flags=re.IGNORECASE)
    if m and len(m.group(1)) >= 6:
        s = m.group(1).strip()
    # Remove duplicated initial phrase (1-3 words)
    dup = re.match(r"^([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2})\s*\1\b", s, flags=re.IGNORECASE)
    if dup:
        s = dup.group(1).strip()
    # Insert space at camelCase boundaries to avoid run-ons like GithubRepository
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return s.strip()
async def _attach_latest_scores(sb, items):
    try:
        items = items or []
        # Gather IDs and, if missing, map homepages to IDs
        ids = [it.get("id") for it in items if it.get("id")]
        missing_id_homes = [it.get("homepage_url") for it in items if not it.get("id") and it.get("homepage_url")]
        home_to_id = {}
        if missing_id_homes:
            try:
                hresp = sb.table("servers").select("id,homepage_url").in_("homepage_url", missing_id_homes).execute()
                for row in (hresp.data or []):
                    home_to_id[row.get("homepage_url")] = row.get("id")
            except Exception:
                pass
        # Attach looked-up IDs back to items
        for it in items:
            if not it.get("id"):
                hid = home_to_id.get(it.get("homepage_url"))
                if hid:
                    it["id"] = hid
                    ids.append(hid)
        if not ids:
            return items
        # Fetch latest scores for all IDs
        resp = sb.table("server_scores").select("server_id,score_overall,breakdown_json,created_at") \
            .in_("server_id", ids).order("created_at", desc=True).execute()
        latest_by_id = {}
        for row in resp.data or []:
            sid = row.get("server_id")
            if sid not in latest_by_id:
                latest_by_id[sid] = {
                    "score_overall": row.get("score_overall"),
                    "breakdown_json": row.get("breakdown_json"),
                    "created_at": row.get("created_at"),
                    "weights": get_rubric_weights(),
                }
        
        # For servers without stored scores, compute them on-demand
        missing_score_ids = [lid for lid in ids if lid not in latest_by_id]
        if missing_score_ids:
            # Fetch server data for missing scores
            server_resp = sb.table("servers").select("id,homepage_url,repo_url,description,tags,updated_at,metadata_json") \
                .in_("id", missing_score_ids).execute()
            
            for server in (server_resp.data or []):
                try:
                    enriched = {
                        "homepage_url": server.get("homepage_url"),
                        "repo_url": server.get("repo_url"),
                        "description": server.get("description"),
                        "tags": server.get("tags") or [],
                    }
                    meta = server.get("metadata_json") or {}
                    if isinstance(meta, dict):
                        enriched.update(meta)
                    
                    newscore = await score_enriched_server(enriched)
                    latest_by_id[server["id"]] = {
                        "score_overall": newscore.get("overall"),
                        "breakdown_json": newscore.get("breakdown"),
                        "created_at": server.get("updated_at"),
                        "weights": get_rubric_weights(),
                    }
                except Exception:
                    # If scoring fails, provide a default
                    latest_by_id[server["id"]] = {
                        "score_overall": None,
                        "breakdown_json": {},
                        "created_at": server.get("updated_at"),
                        "weights": get_rubric_weights(),
                    }
        
        for it in items:
            lid = it.get("id")
            if lid in latest_by_id:
                it["latest_score"] = latest_by_id[lid]
    except Exception:
        pass
    return items



async def _emit_progress(crawl_id: str, interval: float = 20.0):
    # Periodic heartbeat from the backend side
    while controller.active_id() == crawl_id:
        await broker.publish(ProgressEvent(crawl_id, time.time(), "progress", {"heartbeat": True}))
        await asyncio.sleep(interval)


@app.post("/admin/crawl/start", dependencies=[Depends(require_admin_token)])
async def start_crawl(
    enabled_registries: str = "registry_1,registry_2",  # CSV of registry names
    max_pages_registry_1: int = 2,
    max_pages_registry_2: int = 2,
    max_items_registry_1: int | None = None,
    max_items_registry_2: int | None = None,
    crawl_concurrency: int = 6,
    enrich_concurrency: int = 8,
    score_concurrency: int = 8,
    persist: bool = True,
    backfill_after: bool = False,
    bf_batch_size: int = 50,
    bf_enrich_concurrency: int = 1,
    bf_max_items: int | None = None,
):
    if controller.active_id() is not None:
        raise HTTPException(status_code=409, detail="Crawl already running")
    crawl_id = str(uuid.uuid4())

    async def job():
        enabled_list = [r.strip() for r in enabled_registries.split(",") if r.strip()]
        
        crawl = CrawlConfig(
            enabled_registries=enabled_list,
            max_pages_per_registry={
                "registry_1": max(1, int(max_pages_registry_1)),
                "registry_2": max(1, int(max_pages_registry_2)),
            },
            max_items_per_registry={
                "registry_1": max_items_registry_1,
                "registry_2": max_items_registry_2,
            },
        )
        conc = ConcurrencyConfig(
            crawl_concurrency=max(1, int(crawl_concurrency)),
            enrich_concurrency=max(1, int(enrich_concurrency)),
            score_concurrency=max(1, int(score_concurrency)),
        )
        # Fire-and-forget heartbeat
        asyncio.create_task(_emit_progress(crawl_id))
        # Announce crawl start
        await broker.publish(ProgressEvent(crawl_id, time.time(), "progress", {"status": "crawl_started"}))
        http_stats_before = get_http_error_stats(reset=True)
        async def progress_step(data):
            # Relay crawl/backfill granular updates to SSE
            await broker.publish(ProgressEvent(crawl_id, time.time(), "progress", {"crawl_step": data}))
        res = await run_pipeline(crawl, conc, persist_to_supabase=bool(persist), progress_cb=progress_step)
        http_stats_after = get_http_error_stats(reset=False)
        await broker.publish(ProgressEvent(crawl_id, time.time(), "progress", {"summary": res, "http_errors": http_stats_after}))
        # Emit terminal 'done' event so SSE client can close cleanly
        await broker.publish(ProgressEvent(crawl_id, time.time(), "done", {"status": "complete"}))
        # Optionally trigger backfill automatically
        if bool(backfill_after):
            cfg = BackfillConfig(
                batch_size=max(1, int(bf_batch_size)),
                enrich_concurrency=max(1, int(bf_enrich_concurrency)),
                max_items=bf_max_items,
            )

            async def progress(data):
                # Reuse same crawl_id stream for consolidated progress
                await broker.publish(
                    ProgressEvent(crawl_id, time.time(), "progress", {"backfill": data})
                )

            try:
                bf_res = await run_backfill(progress, cfg)
                await broker.publish(
                    ProgressEvent(
                        crawl_id,
                        time.time(),
                        "progress",
                        {"backfill_summary": bf_res},
                    )
                )
                # Emit terminal 'done' after backfill completes as well
                await broker.publish(ProgressEvent(crawl_id, time.time(), "done", {"status": "complete"}))
            except Exception as exc:
                # Treat backfill failures as non-fatal so the stream doesn't close
                await broker.publish(
                    ProgressEvent(
                        crawl_id,
                        time.time(),
                        "progress",
                        {"error": "backfill_failed", "message": str(exc)},
                    )
                )
                # Even on backfill error, signal done for the crawl stream
                await broker.publish(ProgressEvent(crawl_id, time.time(), "done", {"status": "complete_with_backfill_error"}))

    await controller.start(crawl_id, job())
    return {"crawl_id": crawl_id}


@app.post("/admin/crawl/stop", dependencies=[Depends(require_admin_token)])
async def stop_crawl():
    # Force clear without waiting for task completion to prevent hanging
    async with controller._lock:
        if controller._active_task and not controller._active_task.done():
            controller._active_task.cancel()
            # Don't wait for the task to complete - just clear the state
        controller._active_id = None
        controller._active_task = None
    return {"stopped": True}


@app.post("/admin/crawl/forceclear", dependencies=[Depends(require_admin_token)])
async def force_clear_crawl():
    """Force clear stuck crawl state without waiting for task completion"""
    async with controller._lock:
        if controller._active_task and not controller._active_task.done():
            controller._active_task.cancel()
            # Don't wait for the task, just clear the state
        controller._active_id = None
        controller._active_task = None
    return {"force_cleared": True}


@app.get("/admin/crawl/stream", dependencies=[Depends(require_admin_token_flexible)])
async def stream_progress(crawl_id: str):
    async def event_source() -> AsyncIterator[bytes]:
        q = await broker.subscribe(crawl_id)
        try:
            # Immediately inform client that stream is connected
            yield f"data: {json.dumps({'ts': time.time(), 'kind': 'progress', 'data': {'connected': True}})}\n\n".encode()
            while True:
                evt: ProgressEvent = await q.get()
                data = json.dumps({
                    "ts": evt.ts,
                    "kind": evt.kind,
                    "data": evt.data,
                })
                yield f"data: {data}\n\n".encode()
                if evt.kind in ("done", "error"):
                    break
        finally:
            await broker.unsubscribe(crawl_id, q)

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/admin/crawl/status", dependencies=[Depends(require_admin_token)])
async def crawl_status():
    cid = controller.active_id()
    return {"active": cid is not None, "crawl_id": cid}


@app.post("/admin/backfill/start", dependencies=[Depends(require_admin_token)])
async def start_backfill(batch_size: int = 50, enrich_concurrency: int = 3, max_items: int | None = None):
    if backfill_controller.active_id() is not None:
        raise HTTPException(status_code=409, detail="Backfill already running")
    bfid = str(uuid.uuid4())

    async def job():
        cfg = BackfillConfig(batch_size=batch_size, enrich_concurrency=enrich_concurrency, max_items=max_items)
        async def progress(data):
            await broker.publish(ProgressEvent(bfid, time.time(), "progress", data))
        res = await run_backfill(progress, cfg)
        await broker.publish(ProgressEvent(bfid, time.time(), "progress", {"summary": res}))

    await backfill_controller.start(bfid, job())
    return {"backfill_id": bfid}


@app.get("/admin/backfill/stream", dependencies=[Depends(require_admin_token_flexible)])
async def stream_backfill(backfill_id: str):
    async def event_source() -> AsyncIterator[bytes]:
        q = await broker.subscribe(backfill_id)
        try:
            while True:
                evt: ProgressEvent = await q.get()
                data = json.dumps({
                    "ts": evt.ts,
                    "kind": evt.kind,
                    "data": evt.data,
                })
                yield f"data: {data}\n\n".encode()
                if evt.kind in ("done", "error"):
                    break
        finally:
            await broker.unsubscribe(backfill_id, q)

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/admin/backfill/status", dependencies=[Depends(require_admin_token)])
async def backfill_status():
    bid = backfill_controller.active_id()
    return {"active": bid is not None, "backfill_id": bid}


@app.get("/admin/llm/stats", dependencies=[Depends(require_admin_token)])
async def llm_stats(reset: bool = False):
    """Return aggregated Gemini call stats by category.

    Example response:
    {"enrichment": {"attempts":10,"success":6,"429":2,"fail":2}, ...}
    """
    try:
        stats = get_call_stats(reset=bool(reset))
        return {"stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/servers")
async def list_servers(response: Response, limit: int = 20, offset: int = 0, q: Optional[str] = None, sort: Optional[str] = None):
    filters, residual = nl_to_filters(q or "")
    # Clamp and validate sort
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    allowed_sorts = {None, "rank", "stars", "recent", "score"}
    sort_key = (sort or None)
    if sort_key not in allowed_sorts:
        sort_key = None
    try:
        sb = get_supabase_client()
    except SupabaseNotConfigured:
        return {"items": [], "total": 0}
    # Prefer RPCs; on failure, fallback to simple PostgREST filters
    try:
        rpc_params = {
            "query": residual,
            "registry_in": filters.registry_in,
            "tags_any": filters.tags_any,
            "limit_count": limit,
            "offset_count": offset,
            "sort_key": filters.sort or sort_key or "rank",
        }
        items_resp = sb.rpc("search_servers", rpc_params).execute()
        count_resp = sb.rpc("search_servers_count", {
            "query": residual,
            "registry_in": filters.registry_in,
            "tags_any": filters.tags_any,
        }).execute()
        items = items_resp.data or []
        # Clean up names for UI rendering
        for it in items:
            it["name"] = _sanitize_name(it.get("name") or "")
        items = await _attach_latest_scores(sb, items)
        # Note: Post-sorting by score here only sorts the current page results.
        # For proper cross-page sorting, this should be handled at the database level.
        # TODO: Implement database-level score sorting in the RPC or modify query logic.
        total = (count_resp.data or [0])[0] if isinstance(count_resp.data, list) else count_resp.data or 0
        response.headers["X-Total-Count"] = str(total)
        return {"items": items}
    except Exception:
        qh = sb.table("servers").select(
            "id,registry,name,slug,homepage_url,repo_url,description,tags,github_stars,updated_at"
        )
        if filters.registry_in:
            # PostgREST doesn't support IN easily via client; iterate
            # Use 'in' filter once supported; fallback: pick first
            qh = qh.eq("registry", filters.registry_in[0])
        if filters.tags_any:
            try:
                qh = qh.contains("tags", filters.tags_any)
            except Exception:
                pass
        if residual:
            try:
                qh = qh.ilike("name", f"%{residual}%")
            except Exception:
                qh = qh.like("name", f"%{residual}%")
        # Sorting
        key = filters.sort or sort_key
        if key == "stars":
            qh = qh.order("github_stars", desc=True).order("updated_at", desc=True)
        elif key == "recent":
            qh = qh.order("updated_at", desc=True)
        else:
            qh = qh.order("updated_at", desc=True)
        qh = qh.limit(max(1, min(limit, 100))).offset(max(0, offset))
        resp = qh.execute()
        items = resp.data or []
        for it in items:
            it["name"] = _sanitize_name(it.get("name") or "")
        items = await _attach_latest_scores(sb, items)
        if sort_key == "score":
            try:
                items.sort(key=lambda it: float(((it.get("latest_score") or {}).get("score_overall") or -1)), reverse=True)
            except Exception:
                pass
        response.headers["X-Total-Count"] = str(len(items))
        return {"items": items}


@app.get("/search")
async def search_servers(response: Response, q: str, limit: int = 20, offset: int = 0, sort: Optional[str] = None):
    filters, residual = nl_to_filters(q)
    # Clamp
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    allowed_sorts = {None, "rank", "stars", "recent", "score"}
    sort_key = (sort or None)
    if sort_key not in allowed_sorts:
        sort_key = None

    try:
        sb = get_supabase_client()
    except SupabaseNotConfigured:
        return {"items": [], "total": 0}
    try:
        rpc_params = {
            "query": residual,
            "registry_in": filters.registry_in,
            "tags_any": filters.tags_any,
            "limit_count": limit,
            "offset_count": offset,
            "sort_key": filters.sort or sort_key or "rank",
        }
        items_resp = sb.rpc("search_servers", rpc_params).execute()
        count_resp = sb.rpc("search_servers_count", {
            "query": residual,
            "registry_in": filters.registry_in,
            "tags_any": filters.tags_any,
        }).execute()
        items = items_resp.data or []
        for it in items:
            it["name"] = _sanitize_name(it.get("name") or "")
        items = await _attach_latest_scores(sb, items)
        # Note: Score sorting is now handled at the database level in the search_servers RPC function
        total = (count_resp.data or [0])[0] if isinstance(count_resp.data, list) else count_resp.data or 0
        response.headers["X-Total-Count"] = str(total)
        return {"items": items, "total": total}
    except Exception:
        qh = sb.table("servers").select(
            "id,registry,name,slug,homepage_url,repo_url,description,tags,github_stars,updated_at"
        )
        if residual:
            try:
                qh = qh.ilike("name", f"%{residual}%")
            except Exception:
                qh = qh.like("name", f"%{residual}%")
        if filters.registry_in:
            qh = qh.eq("registry", filters.registry_in[0])
        if filters.tags_any:
            try:
                qh = qh.contains("tags", filters.tags_any)
            except Exception:
                pass
        qh = qh.limit(max(1, min(limit, 100))).offset(max(0, offset))
        resp = qh.execute()
        items = resp.data or []
        for it in items:
            it["name"] = _sanitize_name(it.get("name") or "")
        items = await _attach_latest_scores(sb, items)
        if sort_key == "score":
            try:
                items.sort(key=lambda it: float(((it.get("latest_score") or {}).get("score_overall") or -1)), reverse=True)
            except Exception:
                pass
        response.headers["X-Total-Count"] = str(len(items))
        return {"items": items}


@app.get("/servers/{server_id}")
async def get_server_detail(server_id: int, fresh: bool = Query(False)):
    try:
        sb = get_supabase_client()
    except SupabaseNotConfigured:
        raise HTTPException(status_code=404, detail="Not found")
    # Fetch server
    resp = sb.table("servers").select("* ").eq("id", server_id).limit(1).execute()
    items = resp.data or []
    if not items:
        raise HTTPException(status_code=404, detail="Not found")
    server = items[0]
    server["name"] = _sanitize_name(server.get("name") or "")
    # Latest score
    sresp = sb.table("server_scores").select("score_overall,breakdown_json,created_at") \
        .eq("server_id", server_id).order("created_at", desc=True).limit(1).execute()
    sitems = sresp.data or []
    latest_score = sitems[0] if sitems else None
    # Recompute with new rubric if the stored breakdown is from older version, or if fresh requested
    try:
        breakdown = (latest_score or {}).get("breakdown_json") or {}
        # Recompute if explicitly requested, or if old categories, or if baseline now applies
        current_weights = get_rubric_weights()
        baseline_w = float(current_weights.get("baseline", 0) or 0)
        has_new_cats = any(k in breakdown for k in ("runtime_capabilities", "trust_signals", "distribution_host"))
        has_baseline_detail = bool((latest_score or {}).get("details", {}).get("baseline"))
        needs_rescore = bool(
            fresh or (not has_new_cats) or (baseline_w > 0 and (not has_baseline_detail) and (float((latest_score or {}).get("score_overall") or 0) < baseline_w))
        )
        if needs_rescore:
            enriched = {
                "homepage_url": server.get("homepage_url"),
                "repo_url": server.get("repo_url"),
                "description": server.get("description"),
                "tags": server.get("tags") or [],
            }
            meta = server.get("metadata_json") or {}
            if isinstance(meta, dict):
                enriched.update(meta)
            newscore = await score_enriched_server(enriched)
            latest_score = {
                "score_overall": newscore.get("overall"),
                "breakdown_json": newscore.get("breakdown"),
                "created_at": server.get("updated_at"),
            }
            # Surface details if present
            if newscore.get("details"):
                latest_score["details"] = newscore.get("details")
        # If no details present, compute them now and align breakdown/overall in response
        if latest_score is not None and not latest_score.get("details"):
            enriched = {
                "homepage_url": server.get("homepage_url"),
                "repo_url": server.get("repo_url"),
                "description": server.get("description"),
                "tags": server.get("tags") or [],
            }
            meta = server.get("metadata_json") or {}
            if isinstance(meta, dict):
                enriched.update(meta)
            newscore = await score_enriched_server(enriched)
            if newscore.get("details"):
                latest_score["details"] = newscore.get("details")
            # Keep the response consistent with recomputed breakdown/overall
            if newscore.get("breakdown"):
                latest_score["breakdown_json"] = newscore.get("breakdown")
            if newscore.get("overall") is not None:
                latest_score["score_overall"] = newscore.get("overall")
        latest_score["weights"] = current_weights
    except Exception:
        try:
            latest_score["weights"] = get_rubric_weights()
        except Exception:
            pass
    return {"server": server, "latest_score": latest_score}


@app.get("/servers/{server_id}/score")
async def get_server_latest_score(server_id: int, fresh: bool = Query(False)):
    try:
        sb = get_supabase_client()
    except SupabaseNotConfigured:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Try to get stored score first
    sresp = sb.table("server_scores").select("score_overall,breakdown_json,created_at") \
        .eq("server_id", server_id).order("created_at", desc=True).limit(1).execute()
    sitems = sresp.data or []
    
    # If no stored score, compute on-demand
    if not sitems:
        resp = sb.table("servers").select("homepage_url,repo_url,description,tags,updated_at,metadata_json") \
            .eq("id", server_id).limit(1).execute()
        items = resp.data or []
        if not items:
            raise HTTPException(status_code=404, detail="Not found")
        
        server = items[0]
        enriched = {
            "homepage_url": server.get("homepage_url"),
            "repo_url": server.get("repo_url"),
            "description": server.get("description"),
            "tags": server.get("tags") or [],
        }
        meta = server.get("metadata_json") or {}
        if isinstance(meta, dict):
            enriched.update(meta)
        
        newscore = await score_enriched_server(enriched)
        return {
            "score_overall": newscore.get("overall"),
            "breakdown_json": newscore.get("breakdown"),
            "created_at": server.get("updated_at"),
            "weights": get_rubric_weights()
        }
    
    # Use stored score
    latest = sitems[0]
    latest["weights"] = get_rubric_weights()
    return latest


