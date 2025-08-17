from __future__ import annotations

import pandas as pd

from mcp_harvest.features import kmeans_clusters


def test_kmeans_produces_k_clusters():
    rows = []
    for i in range(20):
        rows.append(
            {
                "registry": "mcp-get",
                "server_id": f"srv-{i}",
                "display_name": f"Server {i}",
                "description": "gmail" if i % 2 == 0 else "calendar",
                "runtime": "python" if i % 3 == 0 else "node",
                "install": "",
                "source_repo": "",
                "homepage": "",
                "license": "",
                "maintainer": "",
                "auth_required": "none",
                "env_vars": "[]",
                "tools": "[]",
                "transports": "[\"stdio\"]",
                "registries_seen_in": "[\"mcp-get\"]",
                "last_seen_iso": "2024-01-01T00:00:00Z",
                "first_seen_iso": "2024-01-01T00:00:00Z",
                "fingerprint_sha256": "",
                "reputation_score": 0,
                "tags": "[]",
                "notes": "",
            }
        )
    df = pd.DataFrame(rows)
    result = kmeans_clusters(df, k=5)
    labels = result["labels"]
    assert len(labels) == len(rows)
    assert len(set(labels)) == 5
    assert all(isinstance(x, int) for x in labels)

