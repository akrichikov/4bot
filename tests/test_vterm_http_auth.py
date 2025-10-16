from __future__ import annotations

import json
import sys
import time
from subprocess import Popen, PIPE
import asyncio

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_vterm_http_auth_token_required():
    token = "s3cr3t"
    port = 9892
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port), "--token", token], stdout=PIPE, stderr=PIPE)
    try:
        # wait for health
        start = time.time()
        async with ClientSession() as sess:
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)

            # unauthorized call
            async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo x"}) as r1:
                assert r1.status == 401

            # authorized
            async with ClientSession(headers={"X-VTerm-Token": token}) as s2:
                async with s2.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo ok"}) as r2:
                    data = await r2.json()
                    assert data["exit_code"] == 0
    finally:
        proc.terminate()
