from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List

from mcp_harvest.models import Delta, Fingerprint
from mcp_harvest.storage.io import read_manifest, write_manifest


CORE_KEYS_FOR_FINGERPRINT: List[str] = [
    "display_name",
    "description",
    "runtime",
    "install",
    "source_repo",
    "homepage",
    "license",
    "maintainer",
    "auth_required",
    "env_vars",
    "tools",
    "transports",
    "tags",
]


def stable_manifest_subset(manifest: Dict) -> Dict:
    return {k: manifest.get(k) for k in CORE_KEYS_FOR_FINGERPRINT}


def compute_sha256_for_manifest(manifest: Dict) -> str:
    canonical = json.dumps(stable_manifest_subset(manifest), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_keys(old: Dict | None, new: Dict) -> List[str]:
    if old is None:
        return list(stable_manifest_subset(new).keys())
    changes: List[str] = []
    old_s = stable_manifest_subset(old)
    new_s = stable_manifest_subset(new)
    for key in sorted(set(old_s.keys()) | set(new_s.keys())):
        if old_s.get(key) != new_s.get(key):
            changes.append(key)
    return changes


def update_fingerprint_and_delta(server_id: str, registry: str, manifest: Dict) -> tuple[Fingerprint, Delta | None]:
    previous = read_manifest(server_id)
    new_sha = compute_sha256_for_manifest(manifest)
    now = datetime.now(timezone.utc)
    fp = Fingerprint(server_id=server_id, registry=registry, sha256=new_sha, manifest=manifest, computed_at=now)
    old_sha = None
    delta_obj = None
    if previous is None:
        write_manifest(server_id, manifest)
    else:
        old_sha = compute_sha256_for_manifest(previous)
        if old_sha != new_sha:
            write_manifest(server_id, manifest)
            delta_obj = Delta(
                timestamp=now,
                server_id=server_id,
                registry=registry,
                old_sha=old_sha,
                new_sha=new_sha,
                changed_keys=diff_keys(previous, manifest),
            )
    return fp, delta_obj


