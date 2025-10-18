from __future__ import annotations

import random
from asyncio import sleep
from typing import Awaitable, Callable, TypeVar, Dict

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_fixed


T = TypeVar("T")


async def jitter(min_ms: int, max_ms: int) -> None:
    ms = random.randint(min_ms, max_ms)
    await sleep(ms / 1000.0)


def with_retries(default_attempts: int) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            dyn_attempts = default_attempts
            try:
                self = args[0]
                dyn_attempts = int(getattr(getattr(self, 'cfg', None), 'action_retries', default_attempts) or default_attempts)
            except Exception:
                pass
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max(1, dyn_attempts)),
                retry=retry_if_exception_type(Exception),
                wait=wait_fixed(0.5),
                reraise=True,
            ):
                with attempt:
                    return await fn(*args, **kwargs)
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


def normalize_text(s: str) -> str:
    """Normalize text for loose matching: lower, collapse whitespace."""
    return " ".join(s.lower().split())


class LRUSet:
    """A simple LRU-backed set with fixed capacity.

    add(key) -> bool returns True if the key was not present and is added; False if it was already present.
    When capacity is exceeded, the least-recently-added (oldest) key is evicted.
    """

    def __init__(self, capacity: int = 1024):
        if capacity <= 0:
            capacity = 1
        self.capacity = int(capacity)
        self._map: Dict[str, None] = {}

    def __contains__(self, key: str) -> bool:
        return key in self._map

    def add(self, key: str) -> bool:
        if key in self._map:
            return False
        if len(self._map) >= self.capacity:
            # Evict oldest: rely on insertion order of dict (Python 3.7+ preserves order)
            oldest = next(iter(self._map))
            self._map.pop(oldest, None)
        self._map[key] = None
        return True
