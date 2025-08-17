from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mcp_harvest.cli import app
from mcp_harvest.api import app as fastapi_app


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def test_end_to_end_crawl_query_clusters(tmp_path: Path):
    # Build fixtures in a temp dir
    fixtures = tmp_path / "fixtures"
    _write_json(
        fixtures / "mcp-get" / "packages" / "gmail.json",
        {
            "name": "gmail-python",
            "title": "Gmail Python",
            "description": "Python Gmail server",
            "runtime": "python",
            "install": "uvx mcp-gmail",
            "sourceUrl": "https://github.com/acme/gmail",
            "tags": ["gmail", "email"],
            "env": [{"name": "GMAIL_TOKEN", "required": True}],
            "tools": [{"name": "send_email"}],
        },
    )
    _write_json(
        fixtures / "docker" / "servers" / "gmail.json",
        {
            "id": "docker-gmail",
            "title": "Docker Gmail",
            "description": "Dockerized Gmail server",
            "image": "acme/gmail:latest",
            "curated": True,
            "sourceRepo": "https://github.com/acme/gmail-docker",
            "transports": ["stdio"],
            "tags": ["gmail"],
        },
    )
    _write_json(
        fixtures / "smithery" / "servers.json",
        [
            {
                "id": "smithery-gmail",
                "title": "Smithery Gmail",
                "description": "Gmail server in Smithery",
                "runtime": "python",
                "install": "uvx smithery-gmail",
                "sourceUrl": "https://github.com/acme/smithery-gmail",
                "env": [{"name": "TOKEN", "required": True}],
                "tools": [{"name": "send_email"}],
                "tags": ["gmail"],
            }
        ],
    )
    _write_json(
        fixtures / "opentools" / "servers.json",
        [
            {
                "id": "opentools-gmail",
                "title": "OpenTools Gmail",
                "description": "OpenTools listing",
                "runtime": "node",
                "install": "npx opentools-gmail",
                "sourceUrl": "https://github.com/acme/opentools-gmail",
                "tags": ["gmail"],
            }
        ],
    )
    _write_json(
        fixtures / "mcp-servers" / "servers.json",
        [
            {
                "id": "mcp-servers-gmail",
                "title": "MCP Servers Gmail",
                "description": "Community list",
                "runtime": "python",
                "install": "uvx community-gmail",
                "sourceUrl": "https://github.com/acme/community-gmail",
                "tags": ["gmail"],
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(app, [
        "crawl",
        "--fixtures-dir",
        str(fixtures),
        "--include",
        "smithery,opentools,docker,mcp-get,mcp-servers",
    ])
    assert result.exit_code == 0, result.output

    # servers.csv should contain multiple rows
    df = pd.read_csv(Path("data/servers.csv"))
    assert len(df) >= 5
    assert "gmail-python" in set(df["server_id"])  # sanity check fixture inclusion

    # API smoke
    client = TestClient(fastapi_app)
    r = client.get("/clusters", params={"k": 3})
    assert r.status_code == 200
    payload = r.json()
    assert "labels" in payload and len(payload["labels"]) == len(df)
    assert "top_terms" in payload

