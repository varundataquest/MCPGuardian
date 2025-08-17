from __future__ import annotations

import json
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from mcp_harvest.query import composite_text


RUNTIMES = ["python", "node", "go", "docker-image", "other", "unknown"]
TRANSPORTS = ["stdio", "sse", "streamableHttp", "unknown"]
REGISTRIES = ["smithery", "opentools", "docker", "mcp-get", "mcp-servers"]


def build_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    docs = [composite_text(row) for _, row in df.iterrows()]
    tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    X_text = tfidf.fit_transform(docs)

    # One-hot runtime
    runtime_onehot = np.zeros((len(df), len(RUNTIMES)))
    for i, rt in enumerate(df["runtime"].fillna("unknown").str.lower().tolist()):
        if rt in RUNTIMES:
            runtime_onehot[i, RUNTIMES.index(rt)] = 1

    # Transports bits
    transports_bits = np.zeros((len(df), len(TRANSPORTS)))
    for i, s in enumerate(df["transports"].fillna("[]").tolist()):
        try:
            arr = json.loads(s if isinstance(s, str) else "[]")
        except Exception:
            arr = []
        for t in arr:
            if t in TRANSPORTS:
                transports_bits[i, TRANSPORTS.index(t)] = 1

    # Registry presence bits
    registry_bits = np.zeros((len(df), len(REGISTRIES)))
    for i, s in enumerate(df["registries_seen_in"].fillna("[]").tolist()):
        try:
            arr = json.loads(s if isinstance(s, str) else "[]")
        except Exception:
            arr = []
        for r in arr:
            if r in REGISTRIES:
                registry_bits[i, REGISTRIES.index(r)] = 1

    # Concatenate sparse X_text with dense one-hots
    X_dense = np.hstack([runtime_onehot, transports_bits, registry_bits])
    # Convert X_text to dense cautiously for small datasets
    X = np.hstack([X_text.toarray(), X_dense])
    feature_names = [f"tfidf_{i}" for i in range(X_text.shape[1])] + [
        *(f"runtime_{r}" for r in RUNTIMES),
        *(f"transport_{t}" for t in TRANSPORTS),
        *(f"registry_{r}" for r in REGISTRIES),
    ]
    return X, feature_names


def kmeans_clusters(df: pd.DataFrame, k: int = 12, random_state: int = 42) -> Dict[str, List[int]]:
    if df.empty:
        return {"labels": []}
    n = len(df)
    k = min(max(1, k), n)
    X, _ = build_feature_matrix(df)
    model = KMeans(n_clusters=k, n_init=10, random_state=random_state)
    labels = model.fit_predict(X)
    return {"labels": labels.tolist()}


def plot_clusters(df: pd.DataFrame, labels: List[int], path: str) -> None:
    # Simple bar plot of cluster sizes (no dimensionality reduction for simplicity)
    sizes = {}
    for label in labels:
        sizes[label] = sizes.get(label, 0) + 1
    xs = sorted(sizes.keys())
    ys = [sizes[x] for x in xs]
    plt.figure(figsize=(6, 4))
    plt.bar([str(x) for x in xs], ys)
    plt.title("Cluster sizes")
    plt.xlabel("Cluster")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(path)


def top_terms_per_cluster(df: pd.DataFrame, labels: List[int], top_n: int = 8) -> Dict[int, List[str]]:
    docs = [composite_text(row) for _, row in df.iterrows()]
    vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    X = vectorizer.fit_transform(docs)
    terms = np.array(vectorizer.get_feature_names_out())
    labels_arr = np.array(labels)
    result: Dict[int, List[str]] = {}
    for label in sorted(set(labels)):
        cluster_matrix = X[labels_arr == label]
        if cluster_matrix.shape[0] == 0:
            result[label] = []
            continue
        mean_scores = np.asarray(cluster_matrix.mean(axis=0)).ravel()
        top_idx = np.argsort(-mean_scores)[:top_n]
        result[label] = terms[top_idx].tolist()
    return result


def plot_clusters_to_bytes(df: pd.DataFrame, labels: List[int]) -> bytes:
    sizes = {}
    for label in labels:
        sizes[label] = sizes.get(label, 0) + 1
    xs = sorted(sizes.keys())
    ys = [sizes[x] for x in xs]
    plt.figure(figsize=(6, 4))
    plt.bar([str(x) for x in xs], ys)
    plt.title("Cluster sizes")
    plt.xlabel("Cluster")
    plt.ylabel("Count")
    plt.tight_layout()
    import io

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    return buffer.read()


