from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .config import Config
from .facade import XBot


class Step(BaseModel):
    action: str
    args: Dict[str, Any] = Field(default_factory=dict)
    delay_s: Optional[float] = None


class Playbook(BaseModel):
    steps: List[Step]

    @classmethod
    def from_path(cls, path: Path) -> "Playbook":
        data = json.loads(path.read_text())
        return cls.model_validate(data)


async def run_playbook(path: Path, cfg: Optional[Config] = None) -> None:
    pb = Playbook.from_path(path)
    bot = XBot(cfg or Config.from_env())
    for i, step in enumerate(pb.steps):
        label = step.action.lower().strip().replace("-", "_")
        fn = getattr(bot, label, None)
        if not fn or not callable(fn):
            raise ValueError(f"Unknown action: {step.action}")
        if step.delay_s and step.delay_s > 0:
            await asyncio.sleep(step.delay_s)
        if isinstance(step.args, dict):
            await fn(**step.args)
        else:
            raise ValueError("args must be a dict")

