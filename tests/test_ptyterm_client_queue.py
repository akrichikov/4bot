from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest


@pytest.mark.asyncio
async def test_ptyterm_client_queue_run_wait():
    port = 9915
    # Start server
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
        # Use ptyterm client
        from ptyterm.vterm_client import VTermClient

        client = VTermClient(mode='http', base=f"http://127.0.0.1:{port}")
        jr = await client.queue_run_http("echo client-hello")
        jid = jr["job_id"]
        done = await client.queue_wait_http(jid, timeout=5)
        assert done.get("status") == "done"
        result = done.get("result") or {}
        assert any("client-hello" in ln for ln in (result.get("lines") or []))
    finally:
        proc.terminate()

