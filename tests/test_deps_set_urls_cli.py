from __future__ import annotations

from typer.testing import CliRunner

from xbot.cli import app


def test_deps_pty_set_urls_help():
    runner = CliRunner()
    res = runner.invoke(app, ["deps", "pty-set-urls", "--help"])
    assert res.exit_code == 0, res.output
    assert "GitHub remote URL" in res.output

