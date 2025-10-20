from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_doctor_json_out(tmp_path: Path):
    out = tmp_path / "paths_doctor.json"
    r = CliRunner().invoke(app, ["paths", "doctor", "--json-out", str(out)])
    assert r.exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert "paths" in data and isinstance(data["paths"], dict)
    # check at least logs_dir is reported
    assert "logs_dir" in data["paths"]
