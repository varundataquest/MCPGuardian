import asyncio
import json

from app.agents.registries.mcpso import crawl_mcpso
from app.crew.enrichment import enrich_server_candidate
from app.security.scoring_agent import score_enriched_server


async def main() -> None:
    items = await crawl_mcpso(max_pages=1)
    if not items:
        print(json.dumps({"crawled": 0}))
        return
    enriched = await enrich_server_candidate(items[0])
    scored = await score_enriched_server(enriched)
    print(json.dumps({
        "name": enriched.get("name"),
        "overall": scored["overall"],
        "breakdown": scored["breakdown"],
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


