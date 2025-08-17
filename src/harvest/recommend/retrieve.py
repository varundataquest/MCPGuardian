from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from .embedding import Embedder


def build_corpus(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    ids = df["server_id"].astype(str).tolist() if "server_id" in df.columns else df.index.astype(str).tolist()
    texts = (
        df[["display_name", "description", "tags", "tools"]]
        .astype(str)
        .agg(" ".join, axis=1)
        .tolist()
        if set(["display_name", "description"]).issubset(df.columns)
        else df.astype(str).agg(" ".join, axis=1).tolist()
    )
    return ids, texts


def dense_search(df: pd.DataFrame, query_texts: List[str], top_k: int = 20) -> List[Tuple[str, float]]:
    ids, texts = build_corpus(df)
    emb = Embedder()
    V = emb.encode(texts)
    qv = emb.encode([" ".join(query_texts)])
    sims = (V @ qv.T).ravel()
    idx = np.argsort(-sims)[:top_k]
    return [(ids[i], float(sims[i])) for i in idx]

