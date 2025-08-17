from __future__ import annotations

from mcp_harvest.models import EnvVar, Server, Tool
from mcp_harvest.normalize import server_to_csv_row


def test_server_to_csv_row_has_all_columns():
    server = Server(
        registry="mcp-get",
        server_id="gmail-python",
        display_name="Gmail Python",
        description="Python Gmail server",
        runtime="python",
        env_vars=[EnvVar(name="GMAIL_TOKEN", required=True)],
        tools=[Tool(name="send_email")],
        transports=["stdio"],
        registries_seen_in=["mcp-get"],
        tags=["gmail", "email"],
    )
    row = server_to_csv_row(server)
    # Core columns exist and are non-null
    for key in [
        "registry",
        "server_id",
        "display_name",
        "description",
        "runtime",
        "install",
        "source_repo",
        "homepage",
        "license",
        "maintainer",
        "auth_required",
        "env_vars",
        "tools",
        "transports",
        "registries_seen_in",
        "last_seen_iso",
        "first_seen_iso",
        "fingerprint_sha256",
        "reputation_score",
        "tags",
        "notes",
    ]:
        assert key in row


