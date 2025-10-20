from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_export_writes_all(tmp_path: Path):
    out = tmp_path / "status"
    r = CliRunner().invoke(app, ["paths", "export", "--out-dir", str(out), "--ensure"])
    assert r.exit_code == 0
    for fname in ("paths.json", "paths_env.json", "paths_doctor.json", "paths.md"):
        assert (out / fname).exists(), f"missing {fname}"
