from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_report_scan_secrets_detects_keys(tmp_path: Path):
    src = tmp_path / "logs"
    src.mkdir(parents=True, exist_ok=True)
    (src / "sample.log").write_text("auth_token=abcdef12345\nct0: zyx987", encoding="utf-8")
    r = CliRunner().invoke(app, ["report", "scan-secrets", "--src", str(src)])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["scanned_files"] >= 1
    assert any(m["key"] == "auth_token" for inc in data["incidents"] for m in inc["matches"]) 
