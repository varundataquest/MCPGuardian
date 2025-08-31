import asyncio
from app.security.scoring_agent import score_enriched_server


def test_score_enriched_server_runs():
    enriched = {
        "description": "A test server",
        "tags": ["Official"],
        "repo_url": None,
        "mcp_json": {"tools": [{"name": "http"}]},
    }
    out = asyncio.get_event_loop().run_until_complete(score_enriched_server(enriched))
    assert "overall" in out
    assert 0 <= out["overall"] <= 100
    assert "breakdown" in out

