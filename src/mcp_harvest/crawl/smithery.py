from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from mcp_harvest.models import EnvVar, Server, Tool


class SmitheryCrawler:
    name = "smithery"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")
        self.api_key = os.environ.get("SMITHERY_API_KEY")
        self.client = os.environ.get("SMITHERY_CLIENT", "cursor")

    def _from_cli(self) -> List[Server]:
        try:
            env = os.environ.copy()
            if self.api_key:
                env["SMITHERY_API_KEY"] = self.api_key
            result = subprocess.run(
                ["npx", "-y", "@smithery/cli", "list", "servers", "-client", self.client],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            # Try JSON parse; if not JSON, return empty to avoid bad scraping here
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return []
        except Exception:
            return []
        return self._from_json_records(data)

    def _from_json_records(self, records: List[Dict[str, Any]]) -> List[Server]:
        servers: List[Server] = []
        for r in records:
            envs = [EnvVar(name=e.get("name", ""), required=bool(e.get("required", False)), description=e.get("description")) for e in r.get("env", [])]
            tools = [Tool(name=t.get("name", ""), description=t.get("description")) for t in r.get("tools", [])]
            servers.append(
                Server(
                    registry="smithery",
                    server_id=str(r.get("id") or r.get("slug") or r.get("name") or ""),
                    display_name=r.get("title") or r.get("name"),
                    description=r.get("description"),
                    runtime=(r.get("runtime") or "unknown"),
                    install=r.get("install"),
                    source_repo=r.get("sourceUrl"),
                    homepage=r.get("homepage"),
                    license=r.get("license"),
                    maintainer=r.get("vendor") or r.get("author"),
                    auth_required="api_key" if any(e.get("required") for e in r.get("env", [])) else "none",
                    env_vars=envs,
                    tools=tools,
                    transports=r.get("transports", ["stdio"]),
                    registries_seen_in=["smithery"],
                    tags=r.get("tags", []),
                )
            )
        return servers

    async def run(self) -> List[Server]:
        # Prefer fixtures for determinism
        if self.fixtures_dir:
            path = Path(self.fixtures_dir) / "smithery" / "servers.json"
            if path.exists():
                data = json.loads(path.read_text())
                return self._from_json_records(data)
        # If API key available, try CLI fallback non-interactively
        if self.api_key:
            return self._from_cli()
        # Else, no-op to avoid scraping without auth
        return []


