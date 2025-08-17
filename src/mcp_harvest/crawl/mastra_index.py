from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


class MastraIndexCrawler:
    name = "mastra-index"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self.fixtures_dir = fixtures_dir or os.environ.get("MCP_FIXTURES_DIR")

    async def run(self) -> List[Dict[str, Any]]:
        # This crawler does not emit server rows; it refreshes seeds (out-of-scope here)
        # For determinism, we read fixtures if present and simply return them for observability
        if self.fixtures_dir:
            path = Path(self.fixtures_dir) / "mastra" / "index.json"
            if path.exists():
                data = json.loads(path.read_text())
                return data
        return []


