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
async def test_run_latency_histogram_increments():
    port = 9899
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

            # run with ~0.2s
            cmd = "python -c \"import time; time.sleep(0.2); print('ok')\""
            await sess.post(f"http://127.0.0.1:{port}/run", json={"cmd": cmd})

            async with sess.get(f"http://127.0.0.1:{port}/metrics") as m1:
                after = _parse_metrics(await m1.text())

            # Count should increase by 1
            assert after['vterm_run_duration_seconds_count'] == base.get('vterm_run_duration_seconds_count', 0) + 1
            # Sum should increase by at least 0.1
            assert after['vterm_run_duration_seconds_sum'] >= base.get('vterm_run_duration_seconds_sum', 0) + 0.1
    finally:
        proc.terminate()

