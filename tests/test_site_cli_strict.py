from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_site_build_strict_succeeds(tmp_path: Path, monkeypatch):
    # Ensure roots are valid (defaults are repo-relative)
    out = tmp_path / "site_cli_strict"
    r = CliRunner().invoke(app, ["site", "build", "--out-dir", str(out), "--strict"])
    assert r.exit_code == 0
    assert (out / "paths_validate.json").exists()
