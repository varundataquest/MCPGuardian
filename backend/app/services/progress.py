from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProgressEvent:
    crawl_id: str
    ts: float
    kind: str  # 'started' | 'progress' | 'done' | 'error'
    data: Dict[str, Any] = field(default_factory=dict)


class ProgressBroker:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._last_event: Dict[str, ProgressEvent] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, crawl_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(crawl_id, []).append(q)
            # send last snapshot if exists
            if crawl_id in self._last_event:
                await q.put(self._last_event[crawl_id])
        return q

    async def unsubscribe(self, crawl_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._subscribers.get(crawl_id, [])
            if q in subs:
                subs.remove(q)

    async def publish(self, evt: ProgressEvent) -> None:
        async with self._lock:
            self._last_event[evt.crawl_id] = evt
            subs = list(self._subscribers.get(evt.crawl_id, []))
        for q in subs:
            await q.put(evt)

    def get_last(self, crawl_id: str) -> Optional[ProgressEvent]:
        return self._last_event.get(crawl_id)


class CrawlController:
    def __init__(self, broker: ProgressBroker) -> None:
        self._broker = broker
        self._active_task: Optional[asyncio.Task] = None
        self._active_id: Optional[str] = None
        self._lock = asyncio.Lock()

    async def start(self, crawl_id: str, coro) -> None:
        async with self._lock:
            if self._active_task and not self._active_task.done():
                raise RuntimeError("crawl already running")
            self._active_id = crawl_id

            async def runner():
                try:
                    await self._broker.publish(
                        ProgressEvent(crawl_id, time.time(), "started", {"message": "crawl started"})
                    )
                    await coro
                    await self._broker.publish(
                        ProgressEvent(crawl_id, time.time(), "done", {"message": "crawl done"})
                    )
                except asyncio.CancelledError:
                    await self._broker.publish(
                        ProgressEvent(crawl_id, time.time(), "error", {"message": "crawl cancelled"})
                    )
                    raise
                except Exception as exc:
                    await self._broker.publish(
                        ProgressEvent(crawl_id, time.time(), "error", {"message": str(exc)})
                    )
                finally:
                    # Clear active state to stop heartbeats
                    async with self._lock:
                        self._active_id = None
                        self._active_task = None

            self._active_task = asyncio.create_task(runner())

    async def stop(self) -> None:
        async with self._lock:
            if self._active_task and not self._active_task.done():
                self._active_task.cancel()
                try:
                    await self._active_task
                except asyncio.CancelledError:
                    pass
            self._active_id = None

    def active_id(self) -> Optional[str]:
        return self._active_id


