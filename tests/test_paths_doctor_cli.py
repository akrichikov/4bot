from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_doctor_outputs_expected_keys():
    r = CliRunner().invoke(app, ["paths", "doctor"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert "profile" in data
    assert "paths" in data and isinstance(data["paths"], dict)
    for key in ["logs_dir", "artifacts_dir", "notification_log_dir", "report_html_outdir"]:
        assert key in data["paths"], f"missing {key} in doctor output"
