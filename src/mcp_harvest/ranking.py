from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd

from mcp_harvest.query import search


def _auth_penalty(auth_required: str) -> float:
    if not isinstance(auth_required, str):
        return 0.0
    val = auth_required.lower()
    if val == "none":
        return 0.0
    if val == "api_key":
        return 0.05
    if val == "oauth":
        return 0.08
    return 0.03


def _transport_bonus(transports_json: str) -> float:
    # Prefer stdio slightly (compatibility) and sse moderately
    bonus = 0.0
    s = str(transports_json or "")
    if "stdio" in s:
        bonus += 0.05
    if "sse" in s:
        bonus += 0.03
    return bonus


def _env_var_penalty(env_vars_json: str) -> float:
    # More required env vars imply setup cost
    s = str(env_vars_json or "[]")
    count_required = s.count("\"required\": true")
    return min(0.02 * count_required, 0.1)


def rank_servers(
    df: pd.DataFrame,
    q: str,
    *,
    top: int = 5,
    runtime: Optional[str] = None,
    alpha: float = 0.6,
    beta: float = 0.3,
    gamma: float = 0.1,
) -> List[Dict]:
    idx_scores: List[Tuple[int, float]] = search(df, q, top=max(top * 5, 20), require_runtime=runtime)
    recommendations: List[Dict] = []
    for i, sim in idx_scores:
        row = df.iloc[i]
        rep = float(row.get("reputation_score", 0) or 0) / 100.0
        t_bonus = _transport_bonus(row.get("transports", ""))
        a_pen = _auth_penalty(row.get("auth_required", ""))
        e_pen = _env_var_penalty(row.get("env_vars", ""))
        combined = alpha * float(sim) + beta * rep + gamma * t_bonus - (a_pen + e_pen)
        reasons = []
        reasons.append(f"semantic={sim:.3f}")
        reasons.append(f"reputation={rep*100:.0f}")
        if t_bonus > 0:
            reasons.append("preferred_transport")
        if a_pen > 0:
            reasons.append("auth_friction")
        if e_pen > 0:
            reasons.append("env_setup_cost")
        rec = row.to_dict()
        rec.update({
            "_similarity": sim,
            "_score": float(combined),
            "_reasons": ", ".join(reasons),
        })
        recommendations.append(rec)

    recommendations.sort(key=lambda r: r.get("_score", 0.0), reverse=True)
    return recommendations[:top]

