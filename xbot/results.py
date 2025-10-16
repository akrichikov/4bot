from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config


def _ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def record_action_result(
    label: str,
    success: bool,
    cfg: Config,
    meta: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, str]] = None,
    trace_path: Optional[str] = None,
    har_path: Optional[str] = None,
) -> Path:
    out_dir = Path("artifacts/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_ts()}_{label}.json"
    payload: Dict[str, Any] = {
        "ts": int(time.time()),
        "action": label,
        "success": success,
        "meta": meta or {},
    }
    if artifacts:
        payload["artifacts"] = artifacts
    if trace_path:
        payload["trace"] = trace_path
    if har_path:
        payload["har"] = har_path
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    # also write/update latest.json for convenience
    (out_dir / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    # append to index.jsonl for ingestion
    (out_dir / "index.jsonl").open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
