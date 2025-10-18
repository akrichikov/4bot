from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime
from typing import Dict, List, Optional, Tuple


def _parse_hhmm(s: Optional[str]) -> Optional[dtime]:
    if not s:
        return None
    hh, mm = s.split(":", 1)
    return dtime(hour=int(hh), minute=int(mm))


@dataclass
class Policy:
    name: str
    rps: float
    burst: int
    quiet_start: Optional[str] = None  # "HH:MM"
    quiet_end: Optional[str] = None    # "HH:MM"

    def quiet_window(self) -> Tuple[Optional[dtime], Optional[dtime]]:
        return _parse_hhmm(self.quiet_start), _parse_hhmm(self.quiet_end)


@dataclass
class Bucket:
    tokens: float
    burst: int
    last_ts: float

    def accrue(self, now_ts: float, rps: float) -> None:
        if now_ts <= self.last_ts:
            return
        dt = now_ts - self.last_ts
        self.tokens = min(float(self.burst), self.tokens + dt * max(0.0, rps))
        self.last_ts = now_ts

    def ready(self) -> bool:
        return self.tokens >= 1.0

    def consume(self, amt: float = 1.0) -> bool:
        if self.tokens >= amt:
            self.tokens -= amt
            return True
        return False


def _in_quiet(now: datetime, start: Optional[dtime], end: Optional[dtime]) -> bool:
    if not start or not end:
        return False
    t = now.time()
    if start <= end:
        return start <= t < end
    else:
        # overnight window (e.g., 22:00–06:00)
        return t >= start or t < end


class ProfileScheduler:
    """Per-profile token-bucket scheduler with quiet-hour suppression.

    Usage:
      sched = ProfileScheduler([Policy('a',1,2), Policy('b',2,3)])
      name = sched.pick_next_ready(datetime.now())
      if name:
          sched.record(name, datetime.now())
    """

    def __init__(self, policies: List[Policy]):
        if not policies:
            raise ValueError("policies required")
        self.policies = {p.name: p for p in policies}
        self.order = [p.name for p in policies]
        self._rr_index = 0
        now_ts = 0.0
        self.buckets: Dict[str, Bucket] = {
            p.name: Bucket(tokens=0.0, burst=int(p.burst), last_ts=now_ts)
            for p in policies
        }

    def update(self, now: datetime) -> None:
        ts = now.timestamp()
        for name, b in self.buckets.items():
            pol = self.policies[name]
            b.accrue(ts, pol.rps)

    def pick_next_ready(self, now: datetime) -> Optional[str]:
        self.update(now)
        n = len(self.order)
        for i in range(n):
            idx = (self._rr_index + i) % n
            name = self.order[idx]
            pol = self.policies[name]
            qstart, qend = pol.quiet_window()
            if _in_quiet(now, qstart, qend):
                continue
            if self.buckets[name].ready():
                # advance rr pointer to subsequent position for fairness
                self._rr_index = (idx + 1) % n
                return name
        # advance pointer regardless to avoid stickiness in edge cases
        self._rr_index = (self._rr_index + 1) % n
        return None

    def record(self, name: str, now: datetime, cost: float = 1.0) -> bool:
        if name not in self.buckets:
            return False
        self.update(now)
        return self.buckets[name].consume(cost)
