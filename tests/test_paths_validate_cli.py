from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_validate_outputs_ok_flag():
    r = CliRunner().invoke(app, ["paths", "validate"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert "ok" in data
