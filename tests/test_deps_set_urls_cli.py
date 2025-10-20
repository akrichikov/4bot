from __future__ import annotations

from typer.testing import CliRunner

from xbot.cli import app


def test_deps_group_exists_help():
    runner = CliRunner()
    res = runner.invoke(app, ["deps", "--help"])
    assert res.exit_code == 0, res.output

