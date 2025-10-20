from __future__ import annotations

import asyncio
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_vterm_http_version_endpoint():
    port = 9921
    proc = Popen([sys.executable, "-m", "ptyterm", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        async with ClientSession() as sess:
            # wait health
            start = time.time()
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)
            else:
                raise AssertionError("server did not reach health state")
            # version
            async with sess.get(f"http://127.0.0.1:{port}/version") as r:
                assert r.status == 200
                data = await r.json()
                assert data.get("name") == "ptyterm"
                assert isinstance(data.get("version"), str)
    finally:
        proc.terminate()

