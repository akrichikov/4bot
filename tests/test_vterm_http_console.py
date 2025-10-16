from __future__ import annotations

import sys
import time
from subprocess import Popen, PIPE

from aiohttp import ClientSession
import asyncio
import pytest


@pytest.mark.asyncio
async def test_console_endpoint_serves_html():
    port = 9895
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        async with ClientSession() as sess:
            start = time.time()
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)
            async with sess.get(f"http://127.0.0.1:{port}/console") as r:
                text = await r.text()
                assert r.status == 200
                assert "VTerm Console" in text
                # static asset
            async with sess.get(f"http://127.0.0.1:{port}/static/vterm_console.js") as s:
                js = await s.text()
                assert s.status == 200 and "WebSocket" in js
    finally:
        proc.terminate()
