from __future__ import annotations

import json
import sys
import time
from subprocess import Popen, PIPE

from typer.testing import CliRunner


def test_ptyterm_queue_run_and_wait():
    # start server
    port = 9908
    proc = Popen([sys.executable, "-m", "ptyterm", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        # wait health
        import urllib.request
        t0 = time.time()
        while time.time() - t0 < 5:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.05)

        from ptyterm.__main__ import app as papp
        runner = CliRunner()
        res_run = runner.invoke(papp, ["queue", "run", "echo", "hello", "--target", f"http://127.0.0.1:{port}"])
        assert res_run.exit_code == 0, res_run.output
        jd = json.loads(res_run.stdout)
        jid = jd["job_id"]

        res_wait = runner.invoke(papp, ["queue", "wait", str(jid), "--target", f"http://127.0.0.1:{port}", "--timeout", "5"])
        assert res_wait.exit_code == 0, res_wait.output
        jd2 = json.loads(res_wait.stdout)
        assert jd2.get("status") == "done"
        result = jd2.get("result") or {}
        assert any("hello" in ln for ln in (result.get("lines") or []))
    finally:
        proc.terminate()

