from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_vterm_http_rate_limit_token():
    token = "lim1"
    port = 9893
    # QPS=1, burst=1 so the second request should 429 if immediate
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port), "--token", token, "--rate-qps", "1", "--rate-burst", "1"], stdout=PIPE, stderr=PIPE)
    try:
        # wait for health
        start = time.time()
        async with ClientSession(headers={"X-VTerm-Token": token}) as sess:
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)

            async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo A"}) as r1:
                assert r1.status == 200
            # immediately send another; expect 429
            async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo B"}) as r2:
                assert r2.status == 429
            # wait and try again; should pass
            await asyncio.sleep(1.1)
            async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo C"}) as r3:
                assert r3.status == 200
    finally:
        proc.terminate()

