from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from mcp_harvest.models import CSV_COLUMNS, EnvVar, Server, Tool


def server_to_csv_row(server: Server) -> Dict[str, object]:
    env_vars_json = json.dumps([ev.model_dump() for ev in server.env_vars], ensure_ascii=False, sort_keys=True)
    tools_json = json.dumps([t.model_dump() for t in server.tools], ensure_ascii=False, sort_keys=True)
    transports_json = json.dumps(server.transports, ensure_ascii=False, sort_keys=True)
    registries_json = json.dumps(server.registries_seen_in, ensure_ascii=False, sort_keys=True)
    tags_json = json.dumps(server.tags, ensure_ascii=False, sort_keys=True)

    row = {
        "registry": server.registry,
        "server_id": server.server_id,
        "display_name": server.display_name or "",
        "description": server.description or "",
        "runtime": server.runtime,
        "install": server.install or "",
        "source_repo": server.source_repo or "",
        "homepage": server.homepage or "",
        "license": server.license or "",
        "maintainer": server.maintainer or "",
        "auth_required": server.auth_required,
        "env_vars": env_vars_json,
        "tools": tools_json,
        "transports": transports_json,
        "registries_seen_in": registries_json,
        "last_seen_iso": server.last_seen_iso or datetime.now(timezone.utc).isoformat(),
        "first_seen_iso": server.first_seen_iso or datetime.now(timezone.utc).isoformat(),
        "fingerprint_sha256": server.fingerprint_sha256 or "",
        "reputation_score": server.reputation_score if server.reputation_score is not None else 0,
        "tags": tags_json,
        "notes": server.notes or "",
    }

    # Ensure all CSV columns exist
    for col in CSV_COLUMNS:
        if col not in row:
            row[col] = ""
    return row


