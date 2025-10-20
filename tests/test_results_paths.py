from __future__ import annotations

import json
from pathlib import Path

from xbot.config import Config
from xbot.results import record_action_result


def test_record_action_result_writes_under_cfg_outdir(tmp_path: Path):
    cfg = Config.from_env()
    outdir = tmp_path / "results"
    cfg.report_html_outdir = outdir

    p = record_action_result("unit_test_action", True, cfg, meta={"k": "v"})
    assert p.parent == outdir
    assert p.exists()

    latest = outdir / "latest.json"
    idx = outdir / "index.jsonl"
    assert latest.exists()
    assert idx.exists()
    # Validate JSON shape minimally
    data = json.loads(latest.read_text())
    assert data.get("action") == "unit_test_action"
    assert data.get("success") is True
