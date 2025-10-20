from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from xbot.cli import app


def test_paths_show_json_out(tmp_path: Path):
    out = tmp_path / "paths.json"
    r = CliRunner().invoke(app, ["paths", "show", "--json-out", str(out)])
    assert r.exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert "logs_dir" in data and "artifacts_dir" in data
