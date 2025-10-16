from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_cli_vterm_run_json_output():
    runner = CliRunner()
    # Provide command tokens as separate args so no shell quoting is needed
    result = runner.invoke(app, ["vterm", "run", "printf", "{\"a\":1,\"b\":2}\n"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 0
    assert payload["json_objects"][0]["a"] == 1

