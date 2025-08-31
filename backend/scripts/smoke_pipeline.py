import asyncio
import json

from app.crew.pipeline import run_pipeline, CrawlConfig, ConcurrencyConfig
from dotenv import load_dotenv
import os


async def main() -> None:
    # Load backend/.env if present
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    try:
        load_dotenv(env_path)
    except Exception:
        pass
    crawl = CrawlConfig(max_pages_glama=1, max_pages_mcpso=1)
    conc = ConcurrencyConfig(crawl_concurrency=4, enrich_concurrency=6, score_concurrency=8)
    result = await run_pipeline(crawl_cfg=crawl, conc_cfg=conc, persist_to_supabase=True)
    # Massage samples for display
    samples = []
    for item, score in result["samples"]:
        samples.append({
            "name": item.get("name"),
            "homepage_url": item.get("homepage_url"),
            "overall": score.get("overall"),
        })
    out = {
        "discovered": result["discovered_count"],
        "enriched": result["enriched_count"],
        "scored": result["scored_count"],
        "persisted": result.get("persisted"),
        "samples": samples,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
