from __future__ import annotations

import json
import math
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from ..util import load_config
from .extract import extract
from .retrieve import dense_search
from .rerank import rerank
from mcp_harvest.storage.io import read_servers_csv
from ml.agent_ontology import CAPABILITY_SYNONYMS


def recommend(description: str, top_k: int = 10) -> Dict:
    df = read_servers_csv()
    if df.empty:
        return {"query": description, "results": []}
    q = extract(description)
    # initial dense retrieval by combined text
    queries = q.keywords + q.capabilities
    cand = dense_search(df, queries, top_k=50)
    cand_ids = [cid for cid, _ in cand]
    # pick first capability for rerank; fallback to concatenated queries otherwise
    cap = q.capabilities[0] if q.capabilities else "docs"
    rer = rerank(df, cand_ids, cap)

    # Lexical re-scoring on candidates to boost obvious keyword matches
    subset = df[df["server_id"].astype(str).isin([cid for cid, _ in rer])]
    texts = subset[["display_name", "description", "tags", "tools"]].astype(str).agg(" ".join, axis=1).tolist()
    qtext = " ".join(queries) or description
    if texts:
        tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
        X = tfidf.fit_transform([qtext] + texts)
        lex_scores = (X[0] @ X[1:].T).toarray().ravel()
    else:
        lex_scores = np.zeros(len(texts))

    # Normalize dense and lexical to [0,1] to combine robustly
    dense_map = {cid: s for cid, s in cand}
    dense_vals = np.array([dense_map.get(cid, 0.0) for cid, _ in rer], dtype=float)
    if len(dense_vals) > 0:
        dv = dense_vals
        dv = (dv - dv.min()) / (np.ptp(dv) + 1e-9)
    else:
        dv = np.zeros(0)
    lv = lex_scores
    if len(lv) > 0:
        lv = (lv - lv.min()) / (np.ptp(lv) + 1e-9)

    # Capability keyword prior
    cap_terms = set(CAPABILITY_SYNONYMS.get(cap, []) + [cap])
    def count_matches(text: str) -> int:
        t = text.lower()
        return sum(1 for w in cap_terms if w in t)

    cap_hits = np.array([count_matches(t) for t in texts], dtype=float)
    if cap_hits.size > 0:
        ch = cap_hits / (cap_hits.max() + 1e-9)
    else:
        ch = np.zeros(0)

    # Final blended score: dense 0.6, lexical 0.3, capability prior 0.1
    final_scores = []
    ids_in_order = subset["server_id"].astype(str).tolist()
    for i, cid in enumerate(ids_in_order):
        s = 0.6 * (dv[i] if i < len(dv) else 0.0) + 0.3 * (lv[i] if i < len(lv) else 0.0) + 0.1 * (ch[i] if i < len(ch) else 0.0)
        final_scores.append((cid, float(s)))
    final_scores.sort(key=lambda x: x[1], reverse=True)
    # join scores
    base = {cid: s for cid, s in cand}
    results = []
    def _clean(v):
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass
        return v

    for cid, _p in final_scores[:top_k]:
        row = df[df["server_id"].astype(str) == cid].iloc[0].to_dict()
        dense_sim = base.get(cid, 0.0)
        text = " ".join(str(row.get(k, "")) for k in ["display_name", "description", "tags", "tools"]).lower()
        matched = [w for w in cap_terms if w in text][:5]
        reasons = [f"matches capability '{cap}'"]
        if matched:
            reasons.append(f"matched terms: {', '.join(matched)}")
        reasons.append(f"dense similarity {dense_sim:.3f}")
        rec = {
            "server_id": cid,
            "display_name": row.get("display_name", cid),
            "description": row.get("description", ""),
            "score": round(_p, 3),
            "reasons": reasons,
            "source_repo": row.get("source_repo"),
            "homepage": row.get("homepage"),
        }
        results.append({k: _clean(v) for k, v in rec.items()})
    return {"query": description, "capabilities": q.capabilities, "keywords": q.keywords, "results": results}


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--desc", required=True)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    resp = recommend(args.desc, top_k=args.top)
    print(json.dumps(resp, ensure_ascii=False))

