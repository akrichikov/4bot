from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_queue_run_and_get_status():
    port = 9901
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        async with ClientSession() as sess:
            # wait ready
            start = time.time()
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)

            # enqueue run
            cmd = "python -c \"print('queued')\""
            async with sess.post(f"http://127.0.0.1:{port}/queue/run", json={"cmd": cmd}) as q:
                qd = await q.json()
                assert q.status == 200
                jid = qd["job_id"]

            # poll
            for _ in range(20):
                async with sess.get(f"http://127.0.0.1:{port}/queue/{jid}") as g:
                    gd = await g.json()
                    if gd.get("status") == "done":
                        result = gd.get("result") or {}
                        assert result.get("exit_code") == 0
                        assert any("queued" in ln for ln in (result.get("lines") or []))
                        break
                await asyncio.sleep(0.1)
            else:
                assert False, "job did not finish"
    finally:
        proc.terminate()

