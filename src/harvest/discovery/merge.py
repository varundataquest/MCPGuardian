from __future__ import annotations

from typing import Dict, List

from ..models import ServerCandidate


def key(c: ServerCandidate) -> str:
    k = (str(c.repo_url or c.homepage or c.name or "")).strip().lower()
    return k


def merge_candidates(cands: List[ServerCandidate]) -> List[ServerCandidate]:
    by_key: Dict[str, ServerCandidate] = {}
    for c in cands:
        k = key(c)
        if k in by_key:
            base = by_key[k]
            base.description = base.description or c.description
            base.sdk = base.sdk if base.sdk != "unknown" else c.sdk
            base.transports = sorted(set(base.transports + c.transports))
            base.auth = sorted(set(base.auth + c.auth))
            base.tools = sorted(set(base.tools + c.tools))
            base.registries = sorted(set(base.registries + c.registries))
            base.signals.update(c.signals)
            base.provenance += c.provenance
            base.risk_flags = sorted(set(base.risk_flags + c.risk_flags))
        else:
            by_key[k] = c
    return list(by_key.values())

