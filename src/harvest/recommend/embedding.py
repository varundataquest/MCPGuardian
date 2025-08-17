from __future__ import annotations

import os
from typing import List

import numpy as np


class Embedder:
    def __init__(self) -> None:
        self.test_mode = os.environ.get("RECOMMENDER_TEST_MODE") == "1"
        self._model = None
        if not self.test_mode:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def encode(self, texts: List[str]) -> np.ndarray:
        if self.test_mode:
            # deterministic hash-based pseudo-embeddings to avoid model download in CI
            rng = np.random.default_rng(42)
            vecs = []
            for t in texts:
                h = abs(hash(t)) % (10**8)
                rng = np.random.default_rng(h)
                vecs.append(rng.standard_normal(384))
            return np.vstack(vecs)
        return self._model.encode(texts, normalize_embeddings=True)

