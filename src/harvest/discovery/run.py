import asyncio
import json
from typing import List

from .adapters import github, registries, npm, pypi, dockerhub
from .normalize import normalize_candidate
from .merge import merge_candidates
from .score import score_candidates
from ..util import load_synonyms, writer
from harvest.recommend.extract import extract
from .model import score_candidates_with_model


async def discover(keyword: str, limit: int = 100):
    # Expand terms using LLM-capability extractor when available; fallback to synonyms
    try:
        ex = extract(keyword)
        terms = list(dict.fromkeys((ex.keywords or []) + (ex.capabilities or []))) or load_synonyms(keyword)
    except Exception:
        terms = load_synonyms(keyword)
    hits = []
    hits += await github(terms, limit=limit)
    hits += await registries(terms, limit=limit)
    hits += await npm(terms, limit=limit)
    hits += await pypi(terms, limit=limit)
    hits += await dockerhub(terms, limit=limit)
    cands = [normalize_candidate(h.dict()) if hasattr(h, "dict") else normalize_candidate(h) for h in hits]
    merged = merge_candidates(cands)
    scored = score_candidates(merged, keyword, terms)
    try:
        reranked = score_candidates_with_model(scored)
        # Replace score with model score scaled to 0-100 and add reason
        if reranked:
            items, probs = zip(*reranked)
            out = []
            for it, p in reranked:
                it["score"] = round(float(p) * 100.0, 2)
                it.setdefault("reasons", []).append("ML ranker (weak labels) boosted")
                out.append(it)
            scored = out
    except Exception:
        pass
    writer.write_jsonl(scored, f"data/discover_{keyword.lower().replace(' ', '_')}.jsonl")
    return scored


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--query", "-q", required=True)
    ap.add_argument("--limit", "-k", type=int, default=120)
    args = ap.parse_args()
    res = asyncio.run(discover(args.query, args.limit))
    print(json.dumps(res[:20], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

