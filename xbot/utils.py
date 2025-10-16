from __future__ import annotations

import random
from asyncio import sleep
from typing import Awaitable, Callable, TypeVar

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_fixed


T = TypeVar("T")


async def jitter(min_ms: int, max_ms: int) -> None:
    ms = random.randint(min_ms, max_ms)
    await sleep(ms / 1000.0)


def with_retries(attempts: int) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max(1, attempts)),
                retry=retry_if_exception_type(Exception),
                wait=wait_fixed(0.5),
                reraise=True,
            ):
                with attempt:
                    return await fn(*args, **kwargs)
            # unreachable, but keep type checker happy
            return await fn(*args, **kwargs)

        return wrapper

    return decorator

