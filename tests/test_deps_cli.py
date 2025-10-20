from __future__ import annotations

from typer.testing import CliRunner

from xbot.cli import app


def test_deps_pty_verify_cli():
    runner = CliRunner()
    res = runner.invoke(app, ["deps", "pty-verify"])
    assert res.exit_code == 0, res.output
    assert "ptyterm" in res.output

