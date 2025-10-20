from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_env_contains_expected_keys():
    r = CliRunner().invoke(app, ["paths", "env"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    for k in [
        "PROFILE", "X_PROFILE", "ARTIFACTS_DIR", "LOGS_DIR", "NOTIFICATION_LOG_DIR",
        "REPORT_HTML_OUTDIR", "TRACE_DIR", "HAR_DIR", "STORAGE_STATE", "USER_DATA_DIR",
    ]:
        assert k in data
