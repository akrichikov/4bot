from __future__ import annotations

import asyncio
import sys
import time
from subprocess import Popen, PIPE

import pytest
from aiohttp import ClientSession


def _parse_metrics(text: str) -> dict[str, float]:
    vals = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ' ' in line:
            k, v = line.split(' ', 1)
            try:
                vals[k] = float(v.strip())
            except Exception:
                pass
    return vals


@pytest.mark.asyncio
async def test_metrics_increment():
    port = 9897
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

            async with sess.get(f"http://127.0.0.1:{port}/metrics") as m0:
                base = _parse_metrics(await m0.text())

            # cause a run
            await sess.post(f"http://127.0.0.1:{port}/run", json={"cmd":"echo hi"})
            # and a read
            await sess.get(f"http://127.0.0.1:{port}/read")

            async with sess.get(f"http://127.0.0.1:{port}/metrics") as m1:
                after = _parse_metrics(await m1.text())

            assert after['vterm_requests_total'] >= base.get('vterm_requests_total', 0) + 2
            assert after.get('vterm_requests_by_path{path="/run"}', 0) >= base.get('vterm_requests_by_path{path="/run"}', 0) + 1
            # run exit codes should have grown
            assert any(k.startswith('vterm_run_exit_codes{code="') for k in after.keys())
    finally:
        proc.terminate()

