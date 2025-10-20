from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_site_build_minimal(tmp_path: Path):
    out = tmp_path / "site_cli"
    r = CliRunner().invoke(app, ["site", "build", "--out-dir", str(out)])
    assert r.exit_code == 0
    assert (out / "index.html").exists()
    assert (out / "paths.json").exists()
