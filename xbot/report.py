from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def iter_results(index_path: Path) -> Iterable[Dict[str, Any]]:
    if not index_path.exists():
        return []
    for line in index_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def summary(index_path: Path) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    success: Dict[str, int] = {}
    last_failure: Dict[str, Any] | None = None
    total = 0
    total_ok = 0
    for rec in iter_results(index_path):
        action = rec.get("action", "?")
        ok = bool(rec.get("success", False))
        counts[action] = counts.get(action, 0) + 1
        if ok:
            success[action] = success.get(action, 0) + 1
            total_ok += 1
        else:
            last_failure = rec
        total += 1
    rates = {
        k: (success.get(k, 0) / v if v else 0.0)
        for k, v in counts.items()
    }
    return {
        "total": total,
        "success_total": total_ok,
        "success_rate": (total_ok / total if total else 0.0),
        "by_action": {
            k: {
                "count": counts.get(k, 0),
                "success": success.get(k, 0),
                "rate": rates.get(k, 0.0),
            }
            for k in sorted(counts)
        },
        "last_failure": last_failure,
    }


def export_csv(index_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "action", "success", "meta", "artifacts", "trace", "har"])
        for rec in iter_results(index_path):
            w.writerow([
                rec.get("ts"),
                rec.get("action"),
                1 if rec.get("success") else 0,
                json.dumps(rec.get("meta", {}), ensure_ascii=False),
                json.dumps(rec.get("artifacts", {}), ensure_ascii=False) if rec.get("artifacts") else "",
                rec.get("trace", ""),
                rec.get("har", ""),
            ])

