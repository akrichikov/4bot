from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession, WSMsgType


@pytest.mark.asyncio
async def test_vterm_http_websocket_streams_on_new_output():
    port = 9894
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        # wait for readiness
        async with ClientSession() as sess:
            start = time.time()
            while time.time() - start < 5:
                try:
                    async with sess.get(f"http://127.0.0.1:{port}/health") as r:
                        if r.status == 200:
                            break
                except Exception:
                    await asyncio.sleep(0.05)

            # Connect WS
            ws = await sess.ws_connect(f"http://127.0.0.1:{port}/ws")
            # Prime: write JSON into the vterm
            payload = {"text": "echo '" + json.dumps({"ws": 1}) + "'\n"}
            async with sess.post(f"http://127.0.0.1:{port}/write", json=payload) as w:
                wd = await w.json()
                assert wd["ok"] is True

            # Expect a message with JSON object; tolerate timing variance
            found = False
            for _ in range(10):
                msg = await ws.receive(timeout=1.0)
                assert msg.type == WSMsgType.TEXT
                data = json.loads(msg.data)
                if data.get("json_objects") and data["json_objects"][0].get("ws") == 1:  # type: ignore[index]
                    found = True
                    break
            assert found, "no JSON object streamed from WS"
            await ws.close()
    finally:
        proc.terminate()
