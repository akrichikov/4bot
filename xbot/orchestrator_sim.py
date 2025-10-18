from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from .scheduler_fair import Policy, ProfileScheduler


@dataclass
class WorkSpec:
    name: str
    count: int


def run_sim(
    policies: List[Policy],
    items: List[WorkSpec],
    seconds: int = 30,
    dt_ms: int = 50,
    quiet: Optional[Dict[str, Tuple[str, str]]] = None,
) -> Dict[str, int]:
    # Apply quiet to policies if provided
    if quiet:
        for i, p in enumerate(policies):
            if p.name in quiet:
                qs, qe = quiet[p.name]
                policies[i] = Policy(name=p.name, rps=p.rps, burst=p.burst, quiet_start=qs, quiet_end=qe)
    sch = ProfileScheduler(policies)
    # queues
    queue: Dict[str, int] = {w.name: int(w.count) for w in items}
    processed: Dict[str, int] = {w.name: 0 for w in items}
    now = datetime(2025, 1, 1, 12, 0, 0)
    end = now + timedelta(seconds=max(0, seconds))
    step = timedelta(milliseconds=max(1, dt_ms))
    cur = now
    while cur < end:
        name = sch.pick_next_ready(cur)
        if name and queue.get(name, 0) > 0:
            # Consume work unit if available and token present
            if sch.record(name, cur):
                queue[name] -= 1
                processed[name] += 1
        # Exit early if all queues empty
        if all(v <= 0 for v in queue.values()):
            break
        cur += step
    return processed

