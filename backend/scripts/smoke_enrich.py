import asyncio
import json

from app.agents.registries.mcpso import crawl_mcpso
from app.crew.enrichment import enrich_server_candidate


async def main() -> None:
    items = await crawl_mcpso(max_pages=1)
    print(json.dumps({"crawled": len(items)}, indent=2))
    if not items:
        return
    enriched = await enrich_server_candidate(items[0])
    # Only print a subset for readability
    out = {
        k: enriched.get(k)
        for k in [
            "name",
            "homepage_url",
            "repo_url",
            "description",
            "tags",
            "github",
            "mcp_json",
        ]
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())


