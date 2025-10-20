from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_markdown_writes_file(tmp_path: Path):
    out = tmp_path / "paths.md"
    r = CliRunner().invoke(app, ["paths", "markdown", "--out-md", str(out)])
    assert r.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Paths Summary" in text
    assert "Configured Roots" in text
