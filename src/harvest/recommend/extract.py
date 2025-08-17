from __future__ import annotations

import os
import re
from typing import Dict, List

from pydantic import BaseModel
from openai import OpenAI

from ml.agent_ontology import CAPABILITY_SYNONYMS, ALL_CAPABILITIES


class ExtractedQuery(BaseModel):
    capabilities: List[str]
    keywords: List[str]


_CAP_JOIN = {k: set(v) | {k} for k, v in CAPABILITY_SYNONYMS.items()}


def _heuristic_extract(text: str) -> ExtractedQuery:
    t = text.lower()
    caps: List[str] = []
    kws: List[str] = []
    for cap, syns in _CAP_JOIN.items():
        if any(s in t for s in syns):
            caps.append(cap)
            kws.extend([s for s in syns if s in t])
    # ensure uniqueness and short list
    caps = sorted(set(caps)) or ["docs"]
    kws = sorted(set(kws))[:12]
    return ExtractedQuery(capabilities=caps, keywords=kws)


def extract(text: str) -> ExtractedQuery:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_extract(text)
    client = OpenAI(api_key=api_key)
    prompt = (
        "You are mapping agent descriptions to high-level capabilities. "
        f"Capabilities: {', '.join(ALL_CAPABILITIES)}. "
        "Extract up to 4 capabilities and up to 10 short keywords. Return JSON with keys capabilities, keywords."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        import json

        obj = json.loads(content)
        caps = [c for c in obj.get("capabilities", []) if c in ALL_CAPABILITIES]
        kws = [str(k) for k in obj.get("keywords", [])]
        if not caps:
            return _heuristic_extract(text)
        return ExtractedQuery(capabilities=caps[:4], keywords=kws[:10])
    except Exception:
        return _heuristic_extract(text)

