import math
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from ..models import ServerCandidate

EMB = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def _sem_score(q: str, text: str) -> float:
    if not text:
        return 0.0
    vq = EMB.encode([q], normalize_embeddings=True)
    vt = EMB.encode([text], normalize_embeddings=True)
    return float(np.dot(vq[0], vt[0]))


def _lex_score(q: str, text: str) -> float:
    docs = [q, text]
    tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    X = tfidf.fit_transform(docs)
    sim_mat = (X[0] @ X[1:].T).toarray()
    return float(sim_mat.ravel()[0])


def score_candidates(cands: List[ServerCandidate], keyword: str, terms: List[str]) -> List[dict]:
    out = []
    for c in cands:
        text = " ".join([c.name, c.description])
        sem = max(_sem_score(t, text) for t in terms)
        lex = _lex_score(" ".join(terms), text)
        stars = float(c.signals.get("stars", 0) or 0)
        days = float(c.signals.get("days_since_push", 9999) or 9999)
        recency = 1.0 / (1.0 + math.log1p(max(0.0, days)))
        presence = min(1.0, len(c.registries) / 3.0)
        sdk_bonus = 1.0 if c.sdk in ("typescript", "python") else 0.0
        hygiene = 1.0 if len(c.auth) <= 10 else 0.7
        # Security weighting
        has_risk = bool(getattr(c, "risk_flags", []) )
        risk_penalty = 0.0
        if has_risk:
            risk_penalty = 8.0
        # Slight bonus for declared transports using stdio/sse over custom http
        trans_bonus = 0.0
        if c.transports:
            if "stdio" in c.transports:
                trans_bonus += 1.5
            if "sse" in c.transports:
                trans_bonus += 1.0
        # License / archived adjustments
        lic = (c.signals or {}).get("license")
        archived = bool((c.signals or {}).get("archived", False))
        license_bonus = 1.0 if lic not in (None, "NOASSERTION") else 0.0
        archived_penalty = 12.0 if archived else 0.0

        score = (
            40 * sem
            + 22 * lex
            + 14 * recency
            + 10 * presence
            + 6 * sdk_bonus
            + 4 * hygiene
            + min(4.0, math.log1p(stars))
            + trans_bonus
            + license_bonus
            - risk_penalty
            - archived_penalty
        )
        reasons = []
        if sdk_bonus:
            reasons.append(f"uses official {c.sdk} SDK")
        if presence > 0:
            reasons.append(f"present in {len(c.registries)} registry(ies)")
        if stars > 0:
            reasons.append(f"{int(stars)} GitHub stars")
        if days < 45:
            reasons.append(f"recent activity {int(days)} days ago")
        if trans_bonus > 0:
            reasons.append("standard MCP transport(s)")
        if risk_penalty > 0:
            reasons.append("potentially risky install/docs content detected (penalized)")
        if license_bonus > 0:
            reasons.append("has declared license")
        if archived_penalty > 0:
            reasons.append("archived repository (penalized)")
        c.score = round(score, 2)
        c.reasons = reasons
        out.append(c.model_dump(mode="json"))
    out.sort(key=lambda x: x["score"], reverse=True)
    return out

