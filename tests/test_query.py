from __future__ import annotations

import pandas as pd

from mcp_harvest.storage.io import DATA_DIR, write_servers_csv


def test_query_fixture_contains_python_gmail():
    rows = [
        {
            "registry": "mcp-get",
            "server_id": "gmail-python",
            "display_name": "Gmail Python",
            "description": "Python Gmail server",
            "runtime": "python",
            "install": "uvx mcp-gmail",
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
            "tags": "[\"gmail\"]",
            "notes": "",
        },
        {
            "registry": "docker",
            "server_id": "random",
            "display_name": "Random",
            "description": "A random server",
            "runtime": "node",
            "install": "npx random",
            "source_repo": "",
            "homepage": "",
            "license": "",
            "maintainer": "",
            "auth_required": "none",
            "env_vars": "[]",
            "tools": "[]",
            "transports": "[]",
            "registries_seen_in": "[\"docker\"]",
            "last_seen_iso": "2024-01-01T00:00:00Z",
            "first_seen_iso": "2024-01-01T00:00:00Z",
            "fingerprint_sha256": "",
            "reputation_score": 0,
            "tags": "[]",
            "notes": "",
        },
    ]
    write_servers_csv(rows)

    df = pd.read_csv(DATA_DIR / "servers.csv")
    mask = df["description"].str.contains("python gmail", case=False, na=False) | df["display_name"].str.contains("python gmail", case=False, na=False)
    # Expect at least one match due to 'Gmail Python' and tags/description containing gmail
    assert mask.any()


