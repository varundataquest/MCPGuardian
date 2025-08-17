from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from mcp_harvest.models import Server, Tool


class OpenToolsCrawler:
    name = "opentools"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")
        self.api_key = os.environ.get("OPENTOOLS_API_KEY")

    def _from_records(self, records: List[Dict[str, Any]]) -> List[Server]:
        servers: List[Server] = []
        for r in records:
            tools = [Tool(name=t.get("name", ""), description=t.get("description")) for t in r.get("tools", [])]
            servers.append(
                Server(
                    registry="opentools",
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
                    registries_seen_in=["opentools"],
                    tools=tools,
                    tags=r.get("tags", []),
                )
            )
        return servers

    async def run(self) -> List[Server]:
        if self.fixtures_dir:
            path = Path(self.fixtures_dir) / "opentools" / "servers.json"
            if path.exists():
                data = json.loads(path.read_text())
                return self._from_records(data)
        # Without fixtures, skip network for determinism
        return []


