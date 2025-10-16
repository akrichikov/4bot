from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession, WSMsgType


@pytest.mark.asyncio
async def test_tail_and_ws_replay():
    port = 9896
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

            # generate two outputs
            await sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo one"})
            await sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo two"})

            # tail
            async with sess.get(f"http://127.0.0.1:{port}/tail", params={"limit":"2"}) as t:
                td = await t.json()
                assert t.status == 200
                evs = td.get("events", [])
                assert len(evs) == 2

            # ws replay should emit those two quickly
            ws = await sess.ws_connect(f"http://127.0.0.1:{port}/ws?replay=2")
            got = []
            for _ in range(2):
                msg = await ws.receive(timeout=2.0)
                assert msg.type == WSMsgType.TEXT
                got.append(json.loads(msg.data))
            await ws.close()
            texts = []
            for g in got:
                if g.get("type") == "run":
                    # not guaranteed by replay ordering; accept run/read
                    pass
                txts = g.get("lines") or []
                texts.extend(txts)
            assert any("one" in t for t in texts) or any("two" in t for t in texts)
    finally:
        proc.terminate()

