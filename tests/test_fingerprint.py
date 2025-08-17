from __future__ import annotations

from mcp_harvest.storage.manifest import compute_sha256_for_manifest


def test_fingerprint_stability():
    manifest_a = {
        "display_name": "X",
        "description": "desc",
        "runtime": "python",
        "install": "uvx x",
        "source_repo": "https://github.com/x/y",
        "homepage": None,
        "license": "MIT",
        "maintainer": "me",
        "auth_required": "none",
        "env_vars": [],
        "tools": [],
        "transports": ["stdio"],
        "tags": ["gmail"],
    }
    manifest_b = {k: manifest_a[k] for k in sorted(manifest_a.keys())}
    assert compute_sha256_for_manifest(manifest_a) == compute_sha256_for_manifest(manifest_b)

