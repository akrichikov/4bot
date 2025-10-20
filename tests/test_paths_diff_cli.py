from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_diff_detects_changes(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"logs_dir": "/x/logs", "artifacts_dir": "/x/art"}), encoding="utf-8")
    b.write_text(json.dumps({"logs_dir": "/y/logs", "artifacts_dir": "/x/art", "extra": 1}), encoding="utf-8")
    r = CliRunner().invoke(app, ["paths", "diff", str(a), str(b)])
    assert r.exit_code == 0
    out = json.loads(r.stdout)
    assert "logs_dir" in out["changed"]
    assert "extra" in out["added"]
