from __future__ import annotations

import random
import time
from asyncio import sleep
from typing import Optional


class RateLimiter:
    def __init__(self, min_s: float, max_s: float, enabled: bool = True):
        self.min_s = min_s
        self.max_s = max_s
        self.enabled = enabled
        self._last_ts: Optional[float] = None

    async def wait(self, label: str = "") -> None:
        if not self.enabled:
            return
        now = time.time()
        if self._last_ts is None:
            self._last_ts = now
            return
        elapsed = now - self._last_ts
        target = random.uniform(self.min_s, self.max_s)
        remain = max(0.0, target - elapsed)
        if remain > 0:
            await sleep(remain)
        self._last_ts = time.time()

