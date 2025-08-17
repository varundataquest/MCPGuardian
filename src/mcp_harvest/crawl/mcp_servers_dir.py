from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import httpx

from mcp_harvest.models import Server, Tool


class MCPServersDirCrawler:
    name = "mcp-servers"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")
        self.github_token = os.environ.get("GITHUB_TOKEN")

    def _from_records(self, records: List[Dict[str, Any]]) -> List[Server]:
        servers: List[Server] = []
        for r in records:
            tools = [Tool(name=t.get("name", ""), description=t.get("description")) for t in r.get("tools", [])]
            servers.append(
                Server(
                    registry="mcp-servers",
                    server_id=str(r.get("id") or r.get("slug") or r.get("name") or ""),
                    display_name=r.get("title") or r.get("name"),
                    description=r.get("description"),
                    runtime=(r.get("runtime") or "unknown"),
                    install=r.get("install"),
                    source_repo=r.get("sourceUrl"),
                    homepage=r.get("homepage"),
                    license=r.get("license"),
                    maintainer=r.get("vendor") or r.get("author"),
                    auth_required="none",
                    transports=r.get("transports", ["stdio"]),
                    registries_seen_in=["mcp-servers"],
                    tools=tools,
                    tags=r.get("tags", []),
                )
            )
        return servers

    async def run(self) -> List[Server]:
        if self.fixtures_dir:
            path = Path(self.fixtures_dir) / "mcp-servers" / "servers.json"
            if path.exists():
                data = json.loads(path.read_text())
                return self._from_records(data)
        # Live: parse README of modelcontextprotocol/servers to extract repo links
        headers = {"User-Agent": os.environ.get("USER_AGENT", "mcp-registry-harvester")}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        urls = [
            "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md",
            "https://raw.githubusercontent.com/modelcontextprotocol/servers/master/README.md",
        ]
        content = None
        for url in urls:
            try:
                with httpx.Client(headers=headers, timeout=20.0) as client:
                    r = client.get(url)
                    if r.status_code == 200 and "#" in r.text:
                        content = r.text
                        break
            except Exception:
                continue
        if not content:
            return []

        repo_pattern = re.compile(r"https://github.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
        seen: Set[str] = set()
        records: List[Dict[str, Any]] = []
        for m in repo_pattern.finditer(content):
            owner, repo = m.group(1), m.group(2)
            slug = f"{owner}/{repo}"
            if slug in seen:
                continue
            seen.add(slug)
            records.append(
                {
                    "id": f"mcp-servers:{owner}-{repo}",
                    "title": repo.replace("-", " "),
                    "description": "",
                    "runtime": "unknown",
                    "install": "",
                    "sourceUrl": f"https://github.com/{slug}",
                    "homepage": f"https://github.com/{slug}",
                    "tags": [],
                }
            )
        return self._from_records(records)


