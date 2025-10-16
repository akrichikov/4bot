from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from typing import List, Optional

from .config import Config
from .playbook import run_playbook


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class Task:
    playbook: Path
    times: List[str]  # HH:MM 24h
    days: Optional[List[str]] = None  # e.g., ["mon","wed","fri"]
    jitter_s: float = 0.0
    enabled: bool = True
    last_run: Optional[datetime] = None


@dataclass
class Schedule:
    tasks: List[Task]

    @classmethod
    def from_path(cls, path: Path) -> "Schedule":
        data = json.loads(path.read_text())
        raw_tasks = data.get("tasks", [])
        tasks: List[Task] = []
        for t in raw_tasks:
            tasks.append(
                Task(
                    playbook=Path(t["playbook"]),
                    times=list(t.get("times", [])),
                    days=[d.lower() for d in t.get("days", [])] or None,
                    jitter_s=float(t.get("jitter_s", 0)),
                    enabled=bool(t.get("enabled", True)),
                )
            )
        return cls(tasks=tasks)


def _now() -> datetime:
    return datetime.now()


def _parse_hhmm(s: str) -> dtime:
    hh, mm = s.split(":", 1)
    return dtime(hour=int(hh), minute=int(mm))


def next_run(dt: datetime, task: Task) -> Optional[datetime]:
    if not task.enabled:
        return None
    today_idx = dt.weekday()  # 0=Mon
    allowed_days = (
        set(WEEKDAYS.index(d) for d in task.days) if task.days else set(range(7))
    )
    for day_offset in range(0, 8):
        day_idx = (today_idx + day_offset) % 7
        if day_idx not in allowed_days:
            continue
        base_date = (dt + timedelta(days=day_offset)).date()
        # iterate today’s times if day_offset==0 else all times
        for ts in sorted(task.times):
            t = _parse_hhmm(ts)
            candidate = datetime.combine(base_date, t)
            # apply jitter on the fly (deterministic-ish per minute)
            jitter = timedelta(seconds=task.jitter_s) if task.jitter_s else timedelta(0)
            candidate_j = candidate + jitter
            if candidate_j <= dt:
                continue
            return candidate_j
    return None


async def run_schedule(spec_path: Path, cfg: Optional[Config] = None, once: bool = False, dry_run: bool = False) -> None:
    sched = Schedule.from_path(spec_path)
    bot_cfg = cfg or Config.from_env()
    while True:
        now = _now()
        upcoming: List[tuple[datetime, Task]] = []
        for t in sched.tasks:
            n = next_run(now, t)
            if n is not None:
                upcoming.append((n, t))
        if not upcoming:
            if dry_run or once:
                return
            await asyncio.sleep(30)
            continue
        upcoming.sort(key=lambda x: x[0])
        ntime, ntask = upcoming[0]
        delay = (ntime - _now()).total_seconds()
        if dry_run:
            print(f"NEXT: {ntime.isoformat()} -> {ntask.playbook}")
            return
        if delay > 0:
            await asyncio.sleep(delay)
        await run_playbook(ntask.playbook, bot_cfg)
        ntask.last_run = _now()
        if once:
            return

