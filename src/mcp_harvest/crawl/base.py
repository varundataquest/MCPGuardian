from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

DEFAULT_USER_AGENT = "mcp-registry-harvester (+https://github.com/your-org/mcp-registry-harvester)"


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str


class AbstractCrawler:
    name: str

    def __init__(self, *, rate_limit_seconds: float = 0.7, user_agent: Optional[str] = None) -> None:
        self.rate_limit_seconds = rate_limit_seconds
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AbstractCrawler":
        headers = {"User-Agent": self.user_agent}
        timeout = httpx.Timeout(20.0)
        limits = httpx.Limits(max_connections=10)
        self._client = httpx.AsyncClient(headers=headers, timeout=timeout, limits=limits, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def polite_sleep(self) -> None:
        await asyncio.sleep(self.rate_limit_seconds + random.uniform(0.0, 0.3))

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=2))
    async def fetch_text(self, url: str) -> FetchResult:
        if self._client is None:
            raise RuntimeError("Client not initialized")
        resp = await self._client.get(url)
        await self.polite_sleep()
        resp.raise_for_status()
        return FetchResult(url=url, status_code=resp.status_code, text=resp.text)

    async def run(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


