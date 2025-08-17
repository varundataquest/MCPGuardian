import hashlib
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml


def stable_id(primary: str) -> str:
    s = str(primary) if primary is not None else ""
    return hashlib.sha256(s.strip().lower().encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def load_config():
    with open("configs/discovery.yaml", "r") as f:
        return yaml.safe_load(f)


def load_synonyms(q: str):
    cfg = load_config()
    syn = cfg.get("synonyms", {})
    base = [q]
    base += syn.get(q.lower(), [])
    return list(dict.fromkeys([s.strip() for s in base if s.strip()]))


class writer:
    @staticmethod
    def write_jsonl(items, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")

