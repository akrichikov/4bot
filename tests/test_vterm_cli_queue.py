from __future__ import annotations

import sys
import time
from subprocess import Popen, PIPE

import pytest
from typer.testing import CliRunner

from xbot.cli import app


def test_cli_queue_run_and_wait():
    port = 9902
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        import urllib.request
        # wait for readiness up to 5s
        t0 = time.time()
        while time.time() - t0 < 5:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.05)
        runner = CliRunner()
        res_run = runner.invoke(app, ["vterm","queue","run","echo","cli-queued","--target", f"http://127.0.0.1:{port}"])
        assert res_run.exit_code == 0
        import json
        jd = json.loads(res_run.stdout)
        jid = jd["job_id"]
        res_wait = runner.invoke(app, ["vterm","queue","wait",str(jid),"--target", f"http://127.0.0.1:{port}", "--timeout","5"])
        assert res_wait.exit_code == 0
        jd2 = json.loads(res_wait.stdout)
        assert jd2.get("status") == "done"
        result = jd2.get("result") or {}
        assert any("cli-queued" in ln for ln in (result.get("lines") or []))
    finally:
        proc.terminate()
