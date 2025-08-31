import asyncio
import json

from app.agents.registries.glama import crawl_glama
from app.agents.registries.mcpso import crawl_mcpso


async def main() -> None:
    gl = await crawl_glama(max_pages=1)
    ms = await crawl_mcpso(max_pages=1)
    print(json.dumps({"glama": len(gl), "mcpso": len(ms)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


