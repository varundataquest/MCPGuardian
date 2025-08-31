from __future__ import annotations

from typing import Dict, List
import asyncio

from supabase import Client


async def upsert_servers(sb: Client, items: List[Dict]) -> List[Dict]:
    # Normalize payload for servers table
    rows: List[Dict] = []
    for it in items:
        rows.append({
            "registry": it.get("registry"),
            "name": it.get("name"),
            "slug": it.get("slug"),
            "homepage_url": it.get("homepage_url"),
            "repo_url": it.get("repo_url"),
            "description": it.get("description"),
            "tags": it.get("tags") or [],
            "metadata_json": {k: v for k, v in it.items() if k not in {"registry","name","slug","homepage_url","repo_url","description","tags"}},
            "github_stars": (it.get("github") or {}).get("stargazers_count"),
        })
    # Chunk and retry to be resilient under load
    out: List[Dict] = []
    chunk_size = 500
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        delay = 0.5
        for attempt in range(3):
            try:
                resp = sb.table("servers").upsert(
                    chunk,
                    on_conflict="homepage_url",
                    returning="representation",
                ).execute()
                out.extend(resp.data or [])
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
    return out


async def insert_scores(sb: Client, items_with_scores: List[Dict]) -> None:
    # items_with_scores: list of {"server": enriched, "score": score_dict}
    # Need to map homepage_url -> server_id
    home_to_id: Dict[str, int] = {}
    # Fetch ids in batch
    homes = [x["server"].get("homepage_url") for x in items_with_scores if x.get("server", {}).get("homepage_url")]
    if homes:
        resp = sb.table("servers").select("id,homepage_url").in_("homepage_url", homes).execute()
        for row in resp.data or []:
            home_to_id[row["homepage_url"]] = row["id"]
    rows: List[Dict] = []
    for x in items_with_scores:
        server = x.get("server") or {}
        score = x.get("score") or {}
        sid = home_to_id.get(server.get("homepage_url"))
        if not sid:
            continue
        rows.append({
            "server_id": sid,
            "score_overall": score.get("overall"),
            "breakdown_json": score.get("breakdown"),
        })
    if rows:
        chunk_size = 500
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i+chunk_size]
            delay = 0.5
            for attempt in range(3):
                try:
                    sb.table("server_scores").insert(chunk).execute()
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(delay)
                    delay *= 2


