from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    requests_per_second: float

    def __post_init__(self) -> None:
        self._min_interval = 1.0 / max(self.requests_per_second, 0.001)
        self._last: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait_for = self._last + self._min_interval - now
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last = time.monotonic()


class PerHostRateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self._requests_per_second = requests_per_second
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, host: str) -> None:
        async with self._lock:
            limiter = self._limiters.get(host)
            if limiter is None:
                limiter = RateLimiter(self._requests_per_second)
                self._limiters[host] = limiter
        await limiter.acquire()


# Lightweight HTTP error metrics for benchmarking
_HTTP_ERRORS: int = 0
_HTTP_RETRYABLE: int = 0

def _http_metrics_inc_error() -> None:
    global _HTTP_ERRORS
    _HTTP_ERRORS += 1

def _http_metrics_inc_retryable() -> None:
    global _HTTP_RETRYABLE
    _HTTP_RETRYABLE += 1

def get_http_error_stats(reset: bool = False) -> Dict[str, int]:
    global _HTTP_ERRORS, _HTTP_RETRYABLE
    out = {"errors": int(_HTTP_ERRORS), "retryable": int(_HTTP_RETRYABLE)}
    if reset:
        _HTTP_ERRORS = 0
        _HTTP_RETRYABLE = 0
    return out


async def exponential_backoff_request(
    client: httpx.AsyncClient,
    request_builder: Callable[[], httpx.Request],
    is_retryable: Optional[Callable[[httpx.Response], bool]] = None,
    max_retries: int = 5,
    base_seconds: float = 1.0,
) -> httpx.Response:
    attempt = 0
    while True:
        req = request_builder()
        try:
            # Timeout should be configured on the client; httpx.AsyncClient.send does not accept a timeout kwarg.
            resp = await client.send(req)
        except httpx.HTTPError as exc:
            _http_metrics_inc_error()
            if attempt >= max_retries:
                raise
            delay = base_seconds * (2 ** attempt) * (1 + random.random() * 0.1)
            logger.debug("HTTP error %s, backing off %.2fs", exc, delay)
            await asyncio.sleep(delay)
            attempt += 1
            continue

        if is_retryable is None:
            retryable = resp.status_code in {429, 500, 502, 503, 504}
        else:
            retryable = is_retryable(resp)

        if retryable and attempt < max_retries:
            _http_metrics_inc_retryable()
            delay = base_seconds * (2 ** attempt) * (1 + random.random() * 0.1)
            retry_after = resp.headers.get("retry-after")
            if retry_after is not None:
                with contextlib.suppress(ValueError):
                    delay = max(delay, float(retry_after))
            logger.debug(
                "Retryable status %s, backing off %.2fs", resp.status_code, delay
            )
            await asyncio.sleep(delay)
            attempt += 1
            continue

        return resp


async def fetch_robots_txt(
    url: str,
    client: httpx.AsyncClient,
    per_host_limiter: Optional[PerHostRateLimiter] = None,
    user_agent: str = "MCPGuardianBot/0.1",
) -> Optional[str]:
    """Fetch robots.txt using HEAD (prefer) then GET.

    Returns content string if available; None if not present or disallowed by server.
    """
    parsed = httpx.URL(url)
    robots_url = str(parsed.copy_with(path="/robots.txt", query=None))
    host = parsed.host or ""
    if per_host_limiter is not None:
        await per_host_limiter.acquire(host)

    # Try HEAD first
    try:
        head_resp = await client.head(robots_url, headers={"User-Agent": user_agent})
        if head_resp.status_code == 200 and head_resp.headers.get("content-length", "0") != "0":
            get_resp = await client.get(robots_url, headers={"User-Agent": user_agent})
            return get_resp.text if get_resp.status_code == 200 else None
        elif head_resp.status_code in {403, 404}:
            return None
    except httpx.HTTPError:
        # Fall back to GET
        _http_metrics_inc_error()
        pass

    try:
        get_resp = await client.get(robots_url, headers={"User-Agent": user_agent})
        return get_resp.text if get_resp.status_code == 200 else None
    except httpx.HTTPError:
        _http_metrics_inc_error()
        return None


def is_path_allowed_by_robots(robots_txt: Optional[str], user_agent: str, path: str) -> bool:
    if not robots_txt:
        return True
    # Simple, resilient parser supporting User-agent and Disallow
    ua = None
    disallows = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            ua = line.split(":", 1)[1].strip()
        elif line.lower().startswith("disallow:"):
            rule = line.split(":", 1)[1].strip() or "/"
            if ua in ("*", user_agent):
                disallows.append(rule)

    for rule in disallows:
        if rule == "/":
            return False
        if path.startswith(rule):
            return False
    return True


