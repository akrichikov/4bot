from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from .config import Config


class JsonLogger:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.dir = Path(cfg.logs_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        day = time.strftime("%Y%m%d")
        self.file = self.dir / f"{day}.log"

    def write(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False)
        with self.file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    @asynccontextmanager
    async def action(self, name: str, meta: Optional[Dict[str, Any]] = None) -> AsyncIterator[None]:
        t0 = time.time()
        self.write({"ts": t0, "phase": "start", "name": name, "meta": meta or {}})
        try:
            yield
            self.write({"ts": time.time(), "phase": "end", "name": name, "dur_s": round(time.time() - t0, 3)})
        except Exception as e:
            self.write({
                "ts": time.time(),
                "phase": "error",
                "name": name,
                "dur_s": round(time.time() - t0, 3),
                "error": type(e).__name__,
                "message": str(e),
            })
            raise

    def artifact(self, name: str, paths: Dict[str, str]) -> None:
        self.write({"ts": time.time(), "phase": "artifact", "name": name, "paths": paths})
