from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx

from mcp_harvest.models import EnvVar, Server, Tool


class MCPGetCrawler:
    name = "mcp-get"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")
        self.github_token = os.environ.get("GITHUB_TOKEN")

    async def run(self) -> List[Server]:
        packages: List[Dict[str, Any]] = []
        if self.fixtures_dir:
            pkg_dir = Path(self.fixtures_dir) / "mcp-get" / "packages"
            for path in sorted(pkg_dir.glob("*.json")):
                with open(path) as f:
                    packages.append(json.load(f))
        else:
            # Live fetch via GitHub API
            headers = {"User-Agent": os.environ.get("USER_AGENT", "mcp-registry-harvester")}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            try:
                with httpx.Client(headers=headers, timeout=20.0) as client:
                    resp = client.get("https://api.github.com/repos/michaellatman/mcp-get/contents/packages")
                    resp.raise_for_status()
                    for item in resp.json():
                        if item.get("type") == "file" and item.get("name", "").endswith(".json"):
                            file_resp = client.get(item["url"])  # API contents for file
                            file_resp.raise_for_status()
                            content_obj = file_resp.json()
                            content_b64 = content_obj.get("content", "")
                            try:
                                decoded = base64.b64decode(content_b64).decode("utf-8")
                                packages.append(json.loads(decoded))
                            except Exception:
                                continue
            except Exception:
                packages = []

        servers: List[Server] = []
        for pkg in packages:
            server_id = str(pkg.get("name") or pkg.get("id") or "")
            envs = [EnvVar(name=e.get("name", ""), required=bool(e.get("required", False)), description=e.get("description")) for e in pkg.get("env", [])]
            tools = [Tool(name=t.get("name", ""), description=t.get("description")) for t in pkg.get("tools", [])]
            servers.append(
                Server(
                    registry="mcp-get",
                    server_id=server_id,
                    display_name=pkg.get("title") or pkg.get("name"),
                    description=pkg.get("description"),
                    runtime=(pkg.get("runtime") or "unknown"),
                    install=pkg.get("install") or pkg.get("installCommand"),
                    source_repo=pkg.get("sourceUrl"),
                    homepage=pkg.get("homepage"),
                    license=pkg.get("license"),
                    maintainer=pkg.get("vendor") or pkg.get("author"),
                    auth_required="api_key" if any(e.get("required") for e in pkg.get("env", [])) else "none",
                    env_vars=envs,
                    tools=tools,
                    transports=["stdio"],
                    registries_seen_in=["mcp-get"],
                    tags=pkg.get("tags", []),
                )
            )
        return servers


