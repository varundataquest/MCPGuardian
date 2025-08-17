from __future__ import annotations

import glob
import json
import math
from pathlib import Path
from typing import Iterable, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import csr_matrix, hstack


def _load_jsonl(paths: Iterable[str]) -> pd.DataFrame:
    rows: List[dict] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    rows.append(obj)
                except Exception:
                    continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Fill columns expected downstream
    for col in ["name", "description", "snippet", "signals"]:
        if col not in df.columns:
            df[col] = ""
    return df


def _weak_label(row: pd.Series) -> int:
    # Positive if looks like an MCP server/tool
    text = (str(row.get("name", "")) + " " + str(row.get("description", "")) + " " + str(row.get("snippet", ""))).lower()
    if any(k in text for k in ["mcp", "modelcontextprotocol", "@modelcontextprotocol/sdk", "fastmcp", "mcp server"]):
        return 1
    return 0


def _signals_to_frame(df: pd.DataFrame) -> pd.DataFrame:
    stars = df.get("signals", {}).apply(lambda s: (s or {}).get("stars", 0))
    days = df.get("signals", {}).apply(lambda s: (s or {}).get("days_since_push", 9999))
    archived = df.get("signals", {}).apply(lambda s: 1 if (s or {}).get("archived", False) else 0)
    license_decl = df.get("signals", {}).apply(lambda s: 1 if (s or {}).get("license") not in (None, "NOASSERTION") else 0)
    return pd.DataFrame({
        "stars": stars.astype(float),
        "recency": 1.0 / (1.0 + np.log1p(days.astype(float))),
        "archived": archived.astype(int),
        "has_license": license_decl.astype(int),
    })


def train_from_jsonl(glob_pattern: str, model_path: str = "models/discover_ranker.joblib") -> str:
    paths = sorted(glob.glob(glob_pattern))
    df = _load_jsonl(paths)
    if df.empty:
        raise RuntimeError("No discover data found")
    # Build weak labels
    y = df.apply(_weak_label, axis=1).astype(int).to_numpy()
    # Features
    text = (df.get("name").astype(str) + " " + df.get("description").astype(str) + " " + df.get("snippet").astype(str))
    sig_df = _signals_to_frame(df)

    vectorizer = TfidfVectorizer(min_df=2, ngram_range=(1, 2))
    X_text = vectorizer.fit_transform(text.tolist())
    X_num = np.column_stack([
        sig_df["stars"].to_numpy(dtype=float),
        sig_df["recency"].to_numpy(dtype=float),
        sig_df["archived"].to_numpy(dtype=float),
        sig_df["has_license"].to_numpy(dtype=float),
    ])
    X = hstack([X_text, csr_matrix(X_num)])

    # Guard: ensure at least two classes
    if len(np.unique(y)) < 2:
        # synthesize a tiny positive/negative to let model persist; will act as a neutral scorer
        y = np.concatenate([y, np.array([0, 1])])
        X = hstack([X, X[:2]])

    clf = LogisticRegression(max_iter=500, class_weight="balanced")
    clf.fit(X, y)
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": clf}, model_path)
    return model_path


def score_candidates_with_model(items: List[dict], model_path: str = "models/discover_ranker.joblib") -> List[Tuple[dict, float]]:
    bundle = joblib.load(model_path)
    vectorizer: TfidfVectorizer = bundle["vectorizer"]
    clf: LogisticRegression = bundle["model"]
    if not items:
        return []
    df = pd.DataFrame(items)
    if df.empty:
        return []
    for col in ["name", "description", "snippet", "signals"]:
        if col not in df.columns:
            df[col] = ""
    text = (df.get("name").astype(str) + " " + df.get("description").astype(str) + " " + df.get("snippet").astype(str))
    sig_df = _signals_to_frame(df)
    X_text = vectorizer.transform(text.tolist())
    X_num = np.column_stack([
        sig_df["stars"].to_numpy(dtype=float),
        sig_df["recency"].to_numpy(dtype=float),
        sig_df["archived"].to_numpy(dtype=float),
        sig_df["has_license"].to_numpy(dtype=float),
    ])
    X = hstack([X_text, csr_matrix(X_num)])
    prob = clf.predict_proba(X)[:, 1]
    out = list(zip(items, prob.tolist()))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="data/discover_*.jsonl")
    ap.add_argument("--out", default="models/discover_ranker.joblib")
    args = ap.parse_args()
    path = train_from_jsonl(args.glob, args.out)
    print(json.dumps({"model": path}))


if __name__ == "__main__":
    main()

