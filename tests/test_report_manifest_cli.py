from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_report_manifest_cli(tmp_path: Path):
    d = tmp_path / "status"
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.json").write_text("{}", encoding="utf-8")
    (d / "b.html").write_text("<html></html>", encoding="utf-8")
    out = d / "manifest.json"
    r = CliRunner().invoke(app, ["report", "manifest", "--dir", str(d), "--out", str(out)])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_files"] >= 2
    names = {f["name"] for f in data["files"]}
    assert "a.json" in names and "b.html" in names
