from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
import yaml

from mcp_harvest.models import Server


class DockerRegistryCrawler:
    name = "docker"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")
        self.github_token = os.environ.get("GITHUB_TOKEN")

    async def run(self) -> List[Server]:
        servers: List[Server] = []
        if self.fixtures_dir:
            servers_dir = Path(self.fixtures_dir) / "docker" / "servers"
            for path in sorted(servers_dir.glob("*.json")):
                with open(path) as f:
                    meta: Dict[str, Any] = json.load(f)
                server_id = meta.get("id") or meta.get("name") or Path(path).stem
                description = meta.get("description") or meta.get("summary")
                maintainer = meta.get("maintainer") or meta.get("vendor")
                image = meta.get("image") or meta.get("dockerImage")
                curated = bool(meta.get("curated", False))
                transports = meta.get("transports", ["stdio"])  # default
                runtime = "docker-image"
                servers.append(
                    Server(
                        registry="docker",
                        server_id=str(server_id),
                        display_name=meta.get("title") or str(server_id),
                        description=description,
                        runtime=runtime,
                        install=f"docker run {image}" if image else None,
                        source_repo=meta.get("sourceRepo") or meta.get("sourceUrl"),
                        homepage=meta.get("homepage"),
                        maintainer=maintainer,
                        auth_required="none",
                        transports=transports,
                        registries_seen_in=["docker"],
                        notes="curated" if curated else None,
                        tags=meta.get("tags", []),
                    )
                )
            return servers

        # Live fetch from GitHub: docker/mcp-registry/servers
        headers = {"User-Agent": os.environ.get("USER_AGENT", "mcp-registry-harvester")}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        try:
            with httpx.Client(headers=headers, timeout=20.0) as client:
                resp = client.get("https://api.github.com/repos/docker/mcp-registry/contents/servers")
                resp.raise_for_status()
                for item in resp.json():
                    name = item.get("name", "")
                    if item.get("type") == "file" and (name.endswith(".json") or name.endswith(".yml") or name.endswith(".yaml")):
                        file_resp = client.get(item["url"])  # API contents for file
                        file_resp.raise_for_status()
                        content_obj = file_resp.json()
                        content_b64 = content_obj.get("content", "")
                        try:
                            decoded = base64.b64decode(content_b64).decode("utf-8")
                            if name.endswith(".json"):
                                meta: Dict[str, Any] = json.loads(decoded)
                            else:
                                meta = yaml.safe_load(decoded) or {}
                        except Exception:
                            continue
                        server_id = meta.get("id") or meta.get("name") or item.get("name").removesuffix(".json")
                        description = meta.get("description") or meta.get("summary")
                        maintainer = meta.get("maintainer") or meta.get("vendor")
                        image = meta.get("image") or meta.get("dockerImage")
                        curated = bool(meta.get("curated", False))
                        transports = meta.get("transports", ["stdio"])  # default
                        runtime = "docker-image"
                        servers.append(
                            Server(
                                registry="docker",
                                server_id=str(server_id),
                                display_name=meta.get("title") or str(server_id),
                                description=description,
                                runtime=runtime,
                                install=f"docker run {image}" if image else None,
                                source_repo=meta.get("sourceRepo") or meta.get("sourceUrl"),
                                homepage=meta.get("homepage"),
                                maintainer=maintainer,
                                auth_required="none",
                                transports=transports,
                                registries_seen_in=["docker"],
                                notes="curated" if curated else None,
                                tags=meta.get("tags", []),
                            )
                        )
        except Exception:
            return []
        return servers


