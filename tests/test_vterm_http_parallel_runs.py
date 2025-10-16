from __future__ import annotations

import asyncio
import json
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_parallel_runs_are_serialized():
    port = 9900
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

            async def run(cmd):
                async with sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": cmd}) as r:
                    return await r.json()

            # fire two runs concurrently
            cmd1 = "python -c \"import time; time.sleep(0.1); print('ok1')\""
            cmd2 = "python -c \"import time; time.sleep(0.1); print('ok2')\""
            res1, res2 = await asyncio.gather(run(cmd1), run(cmd2))
            assert res1["exit_code"] == 0 and res2["exit_code"] == 0
            t1 = "\n".join(res1.get("lines", []))
            t2 = "\n".join(res2.get("lines", []))
            assert ("ok1" in t1) or ("ok1" in t2)
            assert ("ok2" in t1) or ("ok2" in t2)
    finally:
        proc.terminate()

