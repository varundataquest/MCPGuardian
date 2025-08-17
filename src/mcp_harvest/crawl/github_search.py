from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx

from mcp_harvest.models import Server


class GithubSearchCrawler:
    name = "github-search"

    def __init__(self) -> None:
        self.github_token = os.environ.get("GITHUB_TOKEN")

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": os.environ.get("USER_AGENT", "mcp-registry-harvester")}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        # topics require a preview header; we will skip topics to keep requests simple
        return headers

    async def run(self) -> List[Server]:
        # Heuristic search: repos mentioning modelcontextprotocol in description/readme
        queries = [
            # General MCP mentions
            "modelcontextprotocol in:readme,description",
            "\"model context protocol\" in:readme,description",
            # Stars/recency heuristic
            "modelcontextprotocol in:readme,description stars:>5 pushed:>2025-04-01",
            # Topics
            "topic:mcp",
            "topic:modelcontextprotocol",
            "topic:mcp-server",
            # Heuristic phrases
            "\"MCP server\" in:readme,description",
            "\"MCP servers\" in:readme,description",
        ]
        servers: List[Server] = []
        try:
            with httpx.Client(headers=self._headers(), timeout=20.0) as client:
                for q in queries:
                    for page in (1, 2):
                        r = client.get(
                            "https://api.github.com/search/repositories",
                            params={"q": q, "per_page": 50, "page": page},
                        )
                        if r.status_code != 200:
                            break
                        data = r.json()
                        for item in data.get("items", []):
                            full_name = item.get("full_name") or ""
                            html_url = item.get("html_url")
                            description = item.get("description")
                            language = (item.get("language") or "").lower() or "unknown"
                            runtime = (
                                "python" if language == "python" else "node" if language in ("javascript", "typescript") else "go" if language == "go" else "unknown"
                            )
                            servers.append(
                                Server(
                                    registry="github",
                                    server_id=f"github:{full_name}",
                                    display_name=full_name,
                                    description=description,
                                    runtime=runtime,
                                    install=None,
                                    source_repo=html_url,
                                    homepage=html_url,
                                    auth_required="unknown",
                                    transports=["unknown"],
                                    registries_seen_in=["github"],
                                    tags=[],
                                )
                            )
        except Exception:
            return []
        return servers

