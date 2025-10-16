from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test_admin_shutdown_with_token():
    port = 9898
    admin = "adm1n"
    proc = Popen([sys.executable, "-m", "xbot.cli", "vterm", "http", "--port", str(port), "--admin-token", admin], stdout=PIPE, stderr=PIPE)
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

            # unauthorized
            async with sess.post(f"http://127.0.0.1:{port}/admin/shutdown") as r0:
                assert r0.status == 401
            # authorized
            async with ClientSession(headers={"X-VTerm-Admin": admin}) as s2:
                async with s2.post(f"http://127.0.0.1:{port}/admin/shutdown") as r1:
                    assert r1.status == 200
            # process should exit shortly
            for _ in range(40):
                rc = proc.poll()
                if rc is not None:
                    break
                await asyncio.sleep(0.05)
            assert proc.poll() is not None
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

