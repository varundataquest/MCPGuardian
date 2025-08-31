from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.db.supabase_client import get_supabase_client
from app.db.repository import upsert_servers, insert_scores
from app.security.scoring_agent import score_enriched_server
from app.llm.gemini import get_optional_client
from app.llm.prompts import build_enrichment_prompt, build_batch_enrichment_prompt, build_batch_reputation_prompt


@dataclass
class BackfillConfig:
    batch_size: int = 50
    enrich_concurrency: int = 3
    max_items: Optional[int] = None


def _is_sparse(server: Dict[str, Any]) -> bool:
    meta = (server.get("metadata_json") or {})
    desc = str(server.get("description") or "").strip()
    tags = server.get("tags") or []
    tools = (meta.get("tools") or [])
    prompts = (meta.get("prompts") or [])
    # gaps
    if not desc or len(desc) < 60:
        return True
    if len(tags) < 2:
        return True
    if not tools and not prompts:
        return True
    if not meta.get("mcp_json"):
        return True
    if (not server.get("repo_url")) and (server.get("project_visibility") == "closed_source"):
        return True
    return False


def _build_enriched_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "registry": row.get("registry"),
        "name": row.get("name"),
        "slug": row.get("slug"),
        "homepage_url": row.get("homepage_url"),
        "repo_url": row.get("repo_url"),
        "description": row.get("description"),
        "tags": row.get("tags") or [],
    }
    meta = (row.get("metadata_json") or {})
    for k in ("mcp_json", "mcp_json_url", "tools", "prompts", "resources", "hosting", "connectivity", "github", "llm_flags"):
        if meta.get(k) is not None:
            out[k] = meta.get(k)
    # derive project visibility
    out["project_visibility"] = "open_source" if out.get("repo_url") else "closed_source"
    return out


async def _maybe_llm_enrich(enriched: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    client = get_optional_client()
    if not client:
        return enriched, False
    # heuristic
    def needs_llm(o: Dict[str, Any]) -> bool:
        desc = str(o.get("description") or "").strip()
        tags = o.get("tags") or []
        tools = o.get("tools") or []
        prompts = o.get("prompts") or []
        if not desc or len(desc) < 60:
            return True
        if len(tags) < 2:
            return True
        if not tools and not prompts:
            return True
        if not o.get("mcp_json"):
            return True
        if (o.get("project_visibility") == "closed_source") and (not o.get("repo_url")):
            return True
        return False

    if not needs_llm(enriched):
        return enriched, False

    parts: List[str] = []
    if enriched.get("description"):
        parts.append(f"Description: {enriched['description']}")
    if enriched.get("tags"):
        parts.append(f"Tags: {', '.join(enriched.get('tags') or [])}")
    if enriched.get("tools"):
        parts.append(
            "Tools: "
            + ", ".join([t if isinstance(t, str) else (t.get("name") or "") for t in (enriched.get("tools") or [])])
        )
    if enriched.get("prompts"):
        parts.append(
            "Prompts: "
            + ", ".join([p if isinstance(p, str) else (p.get("name") or "") for p in (enriched.get("prompts") or [])])
        )
    if enriched.get("mcp_json"):
        parts.append("mcp.json present: true")
    prompt = "\n".join(parts)[:4000]
    try:
        data = await client.generate_json(build_enrichment_prompt(prompt), category="enrichment")
        if isinstance(data, dict):
            if data.get("description") and not enriched.get("description"):
                enriched["description"] = data.get("description")
            if isinstance(data.get("tags"), list):
                merged = list({*(enriched.get("tags") or []), *[str(x) for x in data.get("tags") if x]})
                enriched["tags"] = merged
            if isinstance(data.get("tools"), list) and data.get("tools"):
                enriched["tools"] = data.get("tools")
            if isinstance(data.get("prompts"), list) and data.get("prompts"):
                enriched["prompts"] = data.get("prompts")
            if isinstance(data.get("resources"), list) and data.get("resources"):
                enriched["resources"] = data.get("resources")
            if isinstance(data.get("risk_flags"), dict):
                enriched.setdefault("llm_flags", {}).update(data.get("risk_flags"))
            return enriched, True
    except Exception:
        return enriched, False
    return enriched, False


def _needs_llm(o: Dict[str, Any]) -> bool:
    desc = str(o.get("description") or "").strip()
    tags = o.get("tags") or []
    tools = o.get("tools") or []
    prompts = o.get("prompts") or []
    if not desc or len(desc) < 60:
        return True
    if len(tags) < 2:
        return True
    if not tools and not prompts:
        return True
    if not o.get("mcp_json"):
        return True
    if (o.get("project_visibility") == "closed_source") and (not o.get("repo_url")):
        return True
    return False


def _summarize_enriched(enriched: Dict[str, Any]) -> str:
    parts: List[str] = []
    if enriched.get("description"):
        parts.append(f"Description: {enriched['description']}")
    if enriched.get("tags"):
        parts.append(f"Tags: {', '.join([str(x) for x in (enriched.get('tags') or [])])}")
    if enriched.get("tools"):
        parts.append(
            "Tools: "
            + ", ".join([t if isinstance(t, str) else (t.get("name") or "") for t in (enriched.get("tools") or [])])
        )
    if enriched.get("prompts"):
        parts.append(
            "Prompts: "
            + ", ".join([p if isinstance(p, str) else (p.get("name") or "") for p in (enriched.get("prompts") or [])])
        )
    if enriched.get("mcp_json"):
        parts.append("mcp.json present: true")
    return "\n".join(parts)[:4000]


def _infer_publisher(enriched: Dict[str, Any]) -> Optional[str]:
    repo_url = enriched.get("repo_url") or ""
    try:
        if "github.com" in repo_url:
            parts = httpx.URL(repo_url).path.strip("/").split("/")
            if len(parts) >= 1 and parts[0]:
                return parts[0]
    except Exception:
        return None
    return None


async def _apply_batch_enrichment(client, items: List[Dict[str, Any]], batch_indices: List[int]) -> int:
    if not batch_indices:
        return 0
    indexed_summaries: List[tuple[int, str]] = []
    for i in batch_indices:
        indexed_summaries.append((i, _summarize_enriched(items[i])))
    prompt = build_batch_enrichment_prompt(indexed_summaries)
    data = await client.generate_json(prompt, category="enrichment")
    if not isinstance(data, dict):
        return 1  # counted one call, but no updates
    arr = data.get("items") or []
    if not isinstance(arr, list):
        return 1
    for obj in arr:
        try:
            idx = int(obj.get("index"))
        except Exception:
            continue
        if not (0 <= idx < len(items)):
            continue
        enriched = items[idx]
        if isinstance(obj.get("description"), str) and not enriched.get("description"):
            enriched["description"] = obj.get("description")
        if isinstance(obj.get("tags"), list):
            merged = list({*(enriched.get("tags") or []), *[str(x) for x in obj.get("tags") if x]})
            enriched["tags"] = merged
        if isinstance(obj.get("tools"), list) and obj.get("tools"):
            enriched["tools"] = obj.get("tools")
        if isinstance(obj.get("prompts"), list) and obj.get("prompts"):
            enriched["prompts"] = obj.get("prompts")
        if isinstance(obj.get("resources"), list) and obj.get("resources"):
            enriched["resources"] = obj.get("resources")
        if isinstance(obj.get("risk_flags"), dict):
            enriched.setdefault("llm_flags", {}).update(obj.get("risk_flags"))
    return 1


async def _apply_batch_reputation(client, items: List[Dict[str, Any]], batch_size: int = 12) -> Tuple[int, int]:
    # Collect unique publishers needing reputation
    pubs: List[str] = []
    for s in items:
        if s.get("llm_reputation") is not None:
            continue
        pub = _infer_publisher(s)
        if pub and pub not in pubs:
            pubs.append(pub)
    if not pubs:
        return 0, 0
    calls = 0
    assigned = 0
    for start in range(0, len(pubs), max(1, int(batch_size))):
        chunk = pubs[start:start + max(1, int(batch_size))]
        prompt = build_batch_reputation_prompt(chunk)
        data = await client.generate_json(prompt, category="reputation")
        calls += 1
        if not isinstance(data, dict):
            continue
        arr = data.get("items") or []
        if not isinstance(arr, list):
            continue
        # Build map publisher -> (rep, rationale)
        rep_map: Dict[str, Tuple[float, str]] = {}
        for obj in arr:
            try:
                pub = str(obj.get("publisher") or "").strip()
                comp = float(obj.get("company_reputation"))
            except Exception:
                continue
            rat = str(obj.get("rationale") or "LLM estimate")
            if pub:
                rep_map[pub] = (comp, rat)
        if not rep_map:
            continue
        for s in items:
            pub = _infer_publisher(s)
            if pub and pub in rep_map and s.get("llm_reputation") is None:
                comp, rat = rep_map[pub]
                s["llm_reputation"] = {"company_reputation": comp, "rationale": rat}
                assigned += 1
    return calls, assigned


async def run_backfill(progress_cb, cfg: Optional[BackfillConfig] = None) -> Dict[str, Any]:
    cfg = cfg or BackfillConfig()
    sb = get_supabase_client()

    total_seen = 0
    total_updated = 0
    total_scored = 0
    total_llm_calls = 0
    offset = 0
    started = time.time()

    client = get_optional_client()

    # legacy per-row path removed in favor of true batching

    while True:
        # fetch batch from supabase
        resp = sb.table("servers").select(
            "id,registry,name,slug,homepage_url,repo_url,description,tags,metadata_json"
        ).order("updated_at", desc=True).range(offset, offset + cfg.batch_size - 1).execute()
        rows = resp.data or []
        if not rows:
            break
        offset += len(rows)

        # filter sparse
        candidates = [r for r in rows if _is_sparse(r)]
        if cfg.max_items is not None:
            remaining = max(0, cfg.max_items - total_seen)
            candidates = candidates[:remaining]
        total_seen += len(candidates)
        if not candidates:
            if cfg.max_items is not None and total_seen >= cfg.max_items:
                break
            continue

        # Build enriched list for this batch
        enriched_list: List[Dict[str, Any]] = [_build_enriched_from_row(r) for r in candidates]

        # Batched LLM enrichment where needed
        if client:
            need_indices = [i for i, it in enumerate(enriched_list) if _needs_llm(it)]
            # Chunk to ~10-12 per call to keep prompts small
            for start_idx in range(0, len(need_indices), 12):
                chunk_idx = need_indices[start_idx:start_idx + 12]
                calls_made = await _apply_batch_enrichment(client, enriched_list, chunk_idx)
                total_llm_calls += calls_made
                if progress_cb:
                    await progress_cb({
                        "kind": "progress",
                        "seen": total_seen,
                        "updated": total_updated,
                        "scored": total_scored,
                        "llm_calls": total_llm_calls,
                    })

            # Batched reputation for unique publishers
            calls_made, assigned = await _apply_batch_reputation(client, enriched_list, batch_size=12)
            total_llm_calls += calls_made
            if progress_cb:
                await progress_cb({
                    "kind": "progress",
                    "seen": total_seen,
                    "updated": total_updated,
                    "scored": total_scored,
                    "llm_calls": total_llm_calls,
                })

        # Score concurrently while preserving order
        scores = await asyncio.gather(*[score_enriched_server(e) for e in enriched_list])
        items_with_scores = [{"server": e, "score": s} for e, s in zip(enriched_list, scores)]
        batch_enriched = enriched_list

        if progress_cb:
            await progress_cb({
                "kind": "progress",
                "seen": total_seen,
                "updated": total_updated,
                "scored": total_scored,
                "llm_calls": total_llm_calls,
            })

        if batch_enriched:
            # upsert and score in DB
            await upsert_servers(sb, batch_enriched)
            await insert_scores(sb, items_with_scores)
            total_updated += len(batch_enriched)
            total_scored += len(items_with_scores)

        if cfg.max_items is not None and total_seen >= cfg.max_items:
            break

    return {
        "seen": total_seen,
        "updated": total_updated,
        "scored": total_scored,
        "llm_calls": total_llm_calls,
        "elapsed_sec": round(time.time() - started, 2),
    }


