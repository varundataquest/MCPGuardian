from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx
import logging
import asyncio
from copy import deepcopy
from threading import Lock


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite", request_timeout_s: float = 12.0):
        self.api_key = api_key
        self.model = model
        self.timeout = httpx.Timeout(request_timeout_s)
        self.logger = logging.getLogger(__name__)

    async def generate_text(self, prompt_text: str, *, response_mime_type: Optional[str] = None, temperature: Optional[float] = None) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }
        gen_cfg: Dict[str, Any] = {}
        if response_mime_type:
            gen_cfg["response_mime_type"] = response_mime_type
        if temperature is not None:
            gen_cfg["temperature"] = temperature
        if gen_cfg:
            payload["generationConfig"] = gen_cfg
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return (
            ((data.get("candidates") or [{}])[0]
             .get("content", {})
             .get("parts", [{}])[0]
             .get("text", ""))
        )

    def _extract_first_json_block(self, text: str) -> Optional[Dict[str, Any]]:
        # Try to locate the first balanced JSON object in text
        start = text.find("{")
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                ch = text[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i+1])
                        except Exception:
                            break
            start = text.find("{", start + 1)
        return None

    async def generate_json(self, prompt_text: str, *, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Single-shot call; retry once only on explicit 429 with exponential backoff
        # Apply global rate limit + concurrency limit before each attempt
        attempts = 0
        backoff = 1.0
        while attempts < 2:
            attempts += 1
            _metrics_inc(category, "attempts")
            try:
                await _category_rate_acquire(category)
                await _global_rate_acquire()
                async with _get_category_semaphore(category):
                    async with _GLOBAL_CONCURRENCY:
                        text = await self.generate_text(
                            prompt_text,
                            response_mime_type="application/json",
                            temperature=0.0,
                        )
                text_s = (text or "").strip()
                try:
                    parsed = json.loads(text_s)
                    if isinstance(parsed, dict):
                        _metrics_inc(category, "success")
                        _global_rate_on_success()
                    return parsed if isinstance(parsed, dict) else None
                except Exception:
                    self.logger.warning("gemini: JSON parse failed (len=%d)", len(text_s))
                    block = self._extract_first_json_block(text_s)
                    if isinstance(block, dict):
                        _metrics_inc(category, "success")
                        _global_rate_on_success()
                        return block
                    _metrics_inc(category, "fail")
                    return None
            except httpx.HTTPStatusError as exc:
                if exc.response is not None and exc.response.status_code == 429 and attempts < 2:
                    _metrics_inc(category, "429")
                    self.logger.warning("gemini: 429 received; backing off for %.1fs", backoff)
                    _global_rate_on_429()
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                self.logger.warning("gemini: request failed: %s", exc)
                if exc.response is not None and exc.response.status_code == 429:
                    _metrics_inc(category, "429")
                    _global_rate_on_429()
                else:
                    _metrics_inc(category, "fail")
                return None
            except Exception as exc:
                self.logger.warning("gemini: request failed: %s", exc)
                _metrics_inc(category, "fail")
                return None


def get_optional_client() -> Optional[GeminiClient]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        logging.getLogger(__name__).warning("gemini: GEMINI_API_KEY not set")
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return GeminiClient(key, model=model)


# ------------------------
# Lightweight crawl-time metrics
# ------------------------
_CALLS: Dict[str, Dict[str, int]] = {}
_LOCK = Lock()

def _metrics_inc(category: Optional[str], key: str) -> None:
    if not category:
        return
    with _LOCK:
        d = _CALLS.setdefault(category, {"attempts": 0, "success": 0, "429": 0, "fail": 0})
        d[key] = int(d.get(key, 0)) + 1

def get_call_stats(reset: bool = False) -> Dict[str, Dict[str, int]]:
    with _LOCK:
        out = deepcopy(_CALLS)
        if reset:
            for k in list(_CALLS.keys()):
                _CALLS[k] = {"attempts": 0, "success": 0, "429": 0, "fail": 0}
        return out


# ------------------------
# Global rate limiting (RPM + concurrency)
# ------------------------
class _TokenBucket:
    def __init__(self, rpm: int):
        self.capacity = max(1, int(rpm))
        self.tokens = float(self.capacity)
        self.rate_per_sec = float(rpm) / 60.0
        self.last_refill = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = asyncio.get_event_loop().time()
                elapsed = max(0.0, now - self.last_refill)
                if elapsed > 0.0:
                    self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_sec)
                    self.last_refill = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                # time until next full token
                deficit = 1.0 - self.tokens
                wait_s = max(0.05, deficit / self.rate_per_sec) if self.rate_per_sec > 0 else 1.0
            await asyncio.sleep(wait_s)

    async def set_rpm(self, new_rpm: int) -> None:
        async with self._lock:
            rpm = max(1, int(new_rpm))
            self.capacity = rpm
            self.rate_per_sec = float(rpm) / 60.0
            # Trim tokens if above new capacity
            if self.tokens > self.capacity:
                self.tokens = float(self.capacity)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


_MAX_RPM = _env_int("GEMINI_MAX_RPM", 4000)
_MAX_CONC = _env_int("GEMINI_MAX_CONCURRENCY", 32)
_GLOBAL_BUCKET = _TokenBucket(_MAX_RPM)
_GLOBAL_CONCURRENCY = asyncio.Semaphore(max(1, _MAX_CONC))


async def _global_rate_acquire() -> None:
    await _GLOBAL_BUCKET.acquire()


# ------------------------
# AIMD adaptive tuning
# ------------------------
_MIN_RPM = _env_int("GEMINI_MIN_RPM", 10)
_AIMD_SUCCESS_SINCE_CHANGE = 0


def _get_current_rpm() -> int:
    return int(round(_GLOBAL_BUCKET.rate_per_sec * 60.0))


def _global_rate_on_429() -> None:
    # Multiplicative decrease
    global _AIMD_SUCCESS_SINCE_CHANGE
    _AIMD_SUCCESS_SINCE_CHANGE = 0
    cur = _get_current_rpm()
    new_rpm = max(_MIN_RPM, int(cur * 0.5))
    if new_rpm < cur:
        # Schedule async update without blocking
        asyncio.create_task(_GLOBAL_BUCKET.set_rpm(new_rpm))


def _global_rate_on_success() -> None:
    # Additive increase: +1 RPM after 20 successive successes, up to _MAX_RPM
    global _AIMD_SUCCESS_SINCE_CHANGE
    _AIMD_SUCCESS_SINCE_CHANGE += 1
    if _AIMD_SUCCESS_SINCE_CHANGE >= 20:
        _AIMD_SUCCESS_SINCE_CHANGE = 0
        cur = _get_current_rpm()
        if cur < _MAX_RPM:
            asyncio.create_task(_GLOBAL_BUCKET.set_rpm(cur + 1))


# ------------------------
# Category-specific concurrency and RPM
# ------------------------
from typing import Dict as _Dict_Typing

_CATEGORY_LIMITS: _Dict_Typing[str, int] = {
    "enrichment": _env_int("GEMINI_ENRICH_CONCURRENCY", 1),
    "reputation": _env_int("GEMINI_REPUTE_CONCURRENCY", 1),
}
_CATEGORY_SEMAPHORES: _Dict_Typing[str, asyncio.Semaphore] = {}


def _get_category_semaphore(category: Optional[str]) -> asyncio.Semaphore:
    if not category:
        return _GLOBAL_CONCURRENCY
    sem = _CATEGORY_SEMAPHORES.get(category)
    if sem is None:
        limit = max(1, int(_CATEGORY_LIMITS.get(category, _MAX_CONC)))
        sem = asyncio.Semaphore(limit)
        _CATEGORY_SEMAPHORES[category] = sem
    return sem


_CATEGORY_RPM: _Dict_Typing[str, int] = {
    "enrichment": _env_int("GEMINI_ENRICH_RPM", 20),
    "reputation": _env_int("GEMINI_REPUTE_RPM", 20),
}
_CATEGORY_BUCKETS: _Dict_Typing[str, _TokenBucket] = {}


async def _category_rate_acquire(category: Optional[str]) -> None:
    if not category:
        return
    bucket = _CATEGORY_BUCKETS.get(category)
    if bucket is None:
        rpm = max(1, int(_CATEGORY_RPM.get(category, _MAX_RPM)))
        bucket = _TokenBucket(rpm)
        _CATEGORY_BUCKETS[category] = bucket
    await bucket.acquire()


# ------------------------
# Category-specific concurrency limits
# ------------------------
from typing import Dict as _Dict_Typing

_CATEGORY_LIMITS: _Dict_Typing[str, int] = {
    "enrichment": _env_int("GEMINI_ENRICH_CONCURRENCY", 1),
    "reputation": _env_int("GEMINI_REPUTE_CONCURRENCY", 1),
}
_CATEGORY_SEMAPHORES: _Dict_Typing[str, asyncio.Semaphore] = {}


def _get_category_semaphore(category: Optional[str]) -> asyncio.Semaphore:
    if not category:
        return _GLOBAL_CONCURRENCY
    sem = _CATEGORY_SEMAPHORES.get(category)
    if sem is None:
        limit = max(1, int(_CATEGORY_LIMITS.get(category, _MAX_CONC)))
        sem = asyncio.Semaphore(limit)
        _CATEGORY_SEMAPHORES[category] = sem
    return sem

