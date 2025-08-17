from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SYNONYMS: Dict[str, List[str]] = {
    "gmail": ["gmail", "google mail", "gmail api", "gmail service"],
    "google drive": ["google drive", "drive", "gdrive"],
    "google sheets": ["google sheets", "sheets"],
    "google calendar": ["google calendar", "calendar"],
}


def composite_text(row: pd.Series) -> str:
    parts: List[str] = []
    for key in ["display_name", "description"]:
        val = row.get(key)
        if isinstance(val, str):
            parts.append(val)
    # tags
    try:
        tags = json.loads(row.get("tags", "[]") or "[]")
        parts.extend([str(t) for t in tags])
    except Exception:
        pass
    # tools
    try:
        tools = json.loads(row.get("tools", "[]") or "[]")
        parts.extend([str(t.get("name", "")) for t in tools])
    except Exception:
        pass
    return " ".join(parts)


def expand_query(q: str) -> str:
    text = q
    lower = q.lower()
    for key, syns in SYNONYMS.items():
        if key in lower:
            text += " " + " ".join(syns)
    return text


def search(df: pd.DataFrame, q: str, *, top: int = 5, require_runtime: Optional[str] = None) -> List[Tuple[int, float]]:
    if df.empty:
        return []
    docs = [composite_text(row) for _, row in df.iterrows()]
    vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    X = vectorizer.fit_transform(docs)
    query_vec = vectorizer.transform([expand_query(q)])
    sims = cosine_similarity(query_vec, X).ravel()

    indices = np.argsort(-sims)
    results: List[Tuple[int, float]] = []
    for idx in indices:
        if require_runtime and str(df.iloc[idx]["runtime"]).lower() != require_runtime.lower():
            continue
        results.append((int(idx), float(sims[idx])))
        if len(results) >= top:
            break
    return results


