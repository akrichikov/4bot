from __future__ import annotations

import asyncio
import json
import os
import time
from subprocess import Popen, PIPE
import sys

import pytest
from aiohttp import ClientSession


async def _await_http_ready(port: int, timeout: float = 5.0) -> None:
    start = time.time()
    async with ClientSession() as sess:
        while time.time() - start < timeout:
            try:
                async with sess.get(f"http://127.0.0.1:{port}/health") as resp:
                    if resp.status == 200:
                        return
            except Exception:
                await asyncio.sleep(0.05)
        raise TimeoutError("server not ready")


@pytest.mark.asyncio
async def test_vterm_http_run_write_read():
    port = 9891
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port)], stdout=PIPE, stderr=PIPE)
    try:
        await _await_http_ready(port)
        async with ClientSession() as sess:
            # run echo
            async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": "echo hello"}) as r1:
                data = await r1.json()
                assert data["exit_code"] == 0
                assert any("hello" in ln for ln in data["lines"])  # type: ignore[index]

            # write json and read
            obj = {"a": 5}
            payload = {"text": "echo '" + json.dumps(obj) + "'\n"}
            async with sess.post(f"http://127.0.0.1:{port}/write", json=payload) as w:
                wd = await w.json()
                assert wd["ok"] is True

            async with sess.get(f"http://127.0.0.1:{port}/read", params={"timeout": "0.3"}) as r2:
                data2 = await r2.json()
                assert data2.get("json_objects") and data2["json_objects"][0]["a"] == 5  # type: ignore[index]
    finally:
        proc.terminate()
