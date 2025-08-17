from __future__ import annotations

from mcp_harvest.reputation import compute_reputation


def test_basic_reputation_counts_registries():
    score = compute_reputation(
        registries_seen_in=["docker", "mcp-get", "smithery"],
        curated_docker=True,
        supply_chain_flags={"sbom": True},
        env_vars=[{"name": "TOKEN", "required": True}],
        github_stats=None,
        recency_days=10,
    )
    assert 40 <= score <= 100


