from __future__ import annotations

from typer.testing import CliRunner

from xbot.cli import app


def test_paths_show_contains_roots():
    r = CliRunner().invoke(app, ["paths", "show"])
    assert r.exit_code == 0
    # Basic keys we expect
    for key in ["logs_dir", "artifacts_dir", "report_html_outdir", "notification_log_dir"]:
        assert key in r.stdout
