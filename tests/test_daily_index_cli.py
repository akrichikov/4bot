from __future__ import annotations

import json
import time
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_daily_index_cli(tmp_path: Path):
    res = tmp_path / "results"
    res.mkdir(parents=True, exist_ok=True)
    idx = res / "index.jsonl"
    now = int(time.time())
    yesterday = now - 86400
    # two records across different days
    idx.write_text(
        "\n".join([
            json.dumps({"ts": yesterday, "action": "test", "success": True}),
            json.dumps({"ts": now, "action": "test", "success": False}),
        ]) + "\n",
        encoding="utf-8",
    )
    r = CliRunner().invoke(app, ["report", "daily-index", "--outdir", str(res)])
    assert r.exit_code == 0
    html = (res / "daily" / "index.html").read_text(encoding="utf-8")
    # Should contain day strings in YYYY-MM-DD
    from datetime import datetime
    day_now = datetime.fromtimestamp(now).date().isoformat()
    day_y = datetime.fromtimestamp(yesterday).date().isoformat()
    assert day_now in html and day_y in html
