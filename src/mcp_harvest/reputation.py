from __future__ import annotations

from typing import Dict, List, Optional


def compute_reputation(
    *,
    registries_seen_in: List[str],
    curated_docker: bool = False,
    supply_chain_flags: Optional[Dict[str, bool]] = None,
    env_vars: Optional[List[Dict[str, object]]] = None,
    github_stats: Optional[Dict[str, int]] = None,
    recency_days: Optional[int] = None,
) -> int:
    score = 0
    # Registry presence
    unique_regs = set(registries_seen_in)
    if len(unique_regs) >= 3:
        score += 20
    elif len(unique_regs) == 2:
        score += 10

    # Docker curated and supply chain
    if curated_docker:
        score += 10
    if supply_chain_flags:
        if supply_chain_flags.get("sbom") or supply_chain_flags.get("signed") or supply_chain_flags.get("provenance"):
            score += 10

    # Recency bucket: newer is better
    if recency_days is not None:
        if recency_days <= 7:
            score += 20
        elif recency_days <= 30:
            score += 15
        elif recency_days <= 180:
            score += 10
        elif recency_days <= 365:
            score += 5

    # GitHub health if provided
    if github_stats:
        stars = github_stats.get("stars", 0)
        forks = github_stats.get("forks", 0)
        last_commit_days = github_stats.get("last_commit_days", 9999)
        if stars >= 500:
            score += 20
        elif stars >= 100:
            score += 15
        elif stars >= 25:
            score += 10
        elif stars >= 5:
            score += 5
        if forks >= 20:
            score += 5
        if last_commit_days <= 30:
            score += 5

    # Env var hygiene heuristic
    if env_vars is not None:
        if len(env_vars) > 0:
            score += 5
        excessive = any(str(v.get("name", "")).lower().startswith("root_") for v in env_vars)
        if not excessive:
            score += 5

    return min(score, 100)


