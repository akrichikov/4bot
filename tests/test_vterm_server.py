from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_cli_vterm_server_json_lines():
    runner = CliRunner()

    lines = [
        json.dumps({"cmd": "echo hi"}),
        json.dumps({"cmd": "printf '{\"a\":2}\\n'"}),
    ]
    input_payload = "\n".join(lines) + "\n"

    result = runner.invoke(app, ["vterm", "server"], input=input_payload)
    assert result.exit_code == 0, result.output

    outs = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert len(outs) == 2
    assert outs[0]["exit_code"] == 0 and any("hi" in ln for ln in outs[0]["lines"])  # type: ignore[index]
    assert outs[1]["exit_code"] == 0 and outs[1]["json_objects"][0]["a"] == 2  # type: ignore[index]
