from __future__ import annotations

from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.agent_ontology import CAPABILITY_SYNONYMS


def _weak_label(texts: List[str], capability: str) -> np.ndarray:
    syns = CAPABILITY_SYNONYMS.get(capability, []) + [capability]
    labels = np.array([int(any(s in t.lower() for s in syns)) for t in texts], dtype=int)
    return labels


def train_or_load(df: pd.DataFrame, model_dir: str, capability: str) -> Pipeline:
    import os

    os.makedirs(model_dir, exist_ok=True)
    path = f"{model_dir}/lr_{capability}.joblib"
    if os.path.exists(path):
        return joblib.load(path)
    texts = (
        df[["display_name", "description", "tags", "tools"]]
        .astype(str)
        .agg(" ".join, axis=1)
        .tolist()
        if set(["display_name", "description"]).issubset(df.columns)
        else df.astype(str).agg(" ".join, axis=1).tolist()
    )
    y = _weak_label(texts, capability)
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(min_df=2, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=200, n_jobs=1, class_weight="balanced")),
    ])
    # Guard against single-class labels
    if len(np.unique(y)) < 2:
        stub_texts = ["generic tool", f"{capability} mcp server"]
        stub_y = np.array([0, 1], dtype=int)
        pipe.fit(stub_texts, stub_y)
    else:
        pipe.fit(texts, y)
    joblib.dump(pipe, path)
    return pipe


def rerank(df: pd.DataFrame, candidate_ids: List[str], capability: str, model_dir: str = "models") -> List[Tuple[str, float]]:
    subset = df[df["server_id"].astype(str).isin(candidate_ids)]
    texts = subset[["display_name", "description", "tags", "tools"]].astype(str).agg(" ".join, axis=1).tolist()
    ids = subset["server_id"].astype(str).tolist()
    # Train or load model; if single-class labels or failure, fall back to base order
    try:
        # Quick weak-label check to avoid single-class training
        y_all = _weak_label(
            (
                df[["display_name", "description", "tags", "tools"]]
                .astype(str)
                .agg(" ".join, axis=1)
                .tolist()
                if set(["display_name", "description"]).issubset(df.columns)
                else df.astype(str).agg(" ".join, axis=1).tolist()
            ),
            capability,
        )
        if len(np.unique(y_all)) < 2:
            return [(cid, 0.0) for cid in ids]
        model = train_or_load(df, model_dir, capability)
        proba = model.predict_proba(texts)[:, 1]
        order = np.argsort(-proba)
        return [(ids[i], float(proba[i])) for i in order]
    except Exception:
        return [(cid, 0.0) for cid in ids]

