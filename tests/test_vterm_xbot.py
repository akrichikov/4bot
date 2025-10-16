from __future__ import annotations

import asyncio
import os
import sys
import time
from subprocess import Popen, PIPE

import pytest

from xbot.config import Config
from xbot.facade import XBot


@pytest.mark.asyncio
async def test_xbot_vterm_unix_cycle():
    sock = ".x-vterm-xbot.sock"
    proc = Popen([sys.executable, "-m", "xbot.cli", "vtermd", "start", "--socket-path", sock], stdout=PIPE, stderr=PIPE)
    # wait for socket
    for _ in range(100):
        if os.path.exists(sock):
            break
        time.sleep(0.05)
    try:
        cfg = Config.from_env()
        cfg.vterm_mode = "unix"
        from pathlib import Path
        cfg.vterm_socket = Path(sock)
        bot = XBot(cfg)
        r1 = await bot.vterm_run("echo ping")
        assert r1["exit_code"] == 0 and any("ping" in ln for ln in r1.get("lines", []))
        await bot.vterm_write("echo '{\"q\":9}'\n")
        r2 = await bot.vterm_read(0.3)
        assert r2.get("json_objects") and r2["json_objects"][0]["q"] == 9
    finally:
        proc.terminate()
        try:
            os.unlink(sock)
        except OSError:
            pass
