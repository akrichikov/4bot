from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config
from .report_html import html_report, daily_index
from datetime import datetime


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
    # Use configured report_html_outdir as canonical results directory
    out_dir = Path(cfg.report_html_outdir)
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
    # optional HTML report auto-generation
    try:
        if cfg.report_html_enabled:
            actions_list = None
            if cfg.report_html_actions:
                actions_list = [a.strip() for a in cfg.report_html_actions.split(",") if a.strip()]
            html_report(cfg.report_html_outdir / "index.jsonl", cfg.report_html_outdir / "report.html", actions=actions_list, limit=cfg.report_html_limit)
            if cfg.report_html_daily_enabled:
                day = datetime.fromtimestamp(int(payload.get("ts", 0))).date().isoformat()
                daily_dir = cfg.report_html_outdir / "daily"
                html_report(cfg.report_html_outdir / "index.jsonl", daily_dir / f"{day}.html", actions=actions_list, limit=cfg.report_html_limit, date_str=day)
                daily_index(cfg.report_html_outdir)
    except Exception:
        pass
    return path
