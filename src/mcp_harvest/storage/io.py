from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from mcp_harvest.models import CSV_COLUMNS, Server


DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "manifests").mkdir(parents=True, exist_ok=True)
    servers_csv = DATA_DIR / "servers.csv"
    deltas_csv = DATA_DIR / "deltas.csv"
    if not servers_csv.exists():
        with servers_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
    if not deltas_csv.exists():
        with deltas_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "server_id", "registry", "old_sha", "new_sha", "changed_keys"])


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent)) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def read_servers_csv() -> pd.DataFrame:
    ensure_data_files()
    return pd.read_csv(DATA_DIR / "servers.csv")


def write_servers_csv(rows: List[dict]) -> None:
    ensure_data_files()
    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    tmp_csv = DATA_DIR / "servers.csv.tmp"
    df.to_csv(tmp_csv, index=False)
    os.replace(tmp_csv, DATA_DIR / "servers.csv")


def append_deltas(rows: Iterable[dict]) -> None:
    ensure_data_files()
    deltas_path = DATA_DIR / "deltas.csv"
    tmp_path = DATA_DIR / "deltas.csv.tmp"
    with open(tmp_path, "a", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([
                row.get("timestamp"),
                row.get("server_id"),
                row.get("registry"),
                row.get("old_sha"),
                row.get("new_sha"),
                json.dumps(row.get("changed_keys", []), sort_keys=True),
            ])
    if not deltas_path.exists():
        # Prepend header if file doesn't exist
        with open(deltas_path, "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["timestamp", "server_id", "registry", "old_sha", "new_sha", "changed_keys"])
    # Append new rows atomically
    with open(tmp_path, "r") as f_in, open(deltas_path, "a") as f_out:
        f_out.write(f_in.read())
    os.remove(tmp_path)


def write_manifest(server_id: str, manifest: dict) -> Path:
    ensure_data_files()
    path = DATA_DIR / "manifests" / f"{server_id}.json"
    atomic_write_text(path, json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2))
    return path


def read_manifest(server_id: str) -> Optional[dict]:
    path = DATA_DIR / "manifests" / f"{server_id}.json"
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


