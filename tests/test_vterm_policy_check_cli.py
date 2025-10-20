from __future__ import annotations

import json
from typer.testing import CliRunner

from xbot.cli import app


def test_vterm_policy_check_evaluates_samples():
    runner = CliRunner()
    res = runner.invoke(app, [
        "vterm", "policy-check",
        "--allow", r"^echo\b",
        "--deny", r"rm",
        "--sample", "echo ok",
        "--sample", "ls",
        "--sample", "rm -rf /",
    ])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.stdout)
    samples = {s["cmd"]: s["authorized"] for s in payload.get("samples", [])}
    assert samples["echo ok"] is True
    assert samples["ls"] is False
    assert samples["rm -rf /"] is False

