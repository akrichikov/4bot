from __future__ import annotations

import json
import os
import time
from pathlib import Path
from subprocess import Popen, PIPE
import sys

import pytest

from xbot.vtermd import client_request, DEFAULT_SOCKET


def _start_daemon(socket_path: str, init_cmd: str | None = None) -> Popen:
    args = [sys.executable, "-m", "xbot.cli", "vtermd", "start", "--socket-path", socket_path]
    if init_cmd:
        args += ["--init-cmd", init_cmd]
    # Spawn in background
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    # Wait briefly for socket to appear
    for _ in range(100):
        if os.path.exists(socket_path):
            break
        time.sleep(0.05)
    # If the process died early, expose stderr for debugging
    if not os.path.exists(socket_path) and proc.poll() is not None:
        try:
            err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        except Exception:
            err = ""
        raise RuntimeError(f"vtermd failed to start. rc={proc.returncode} stderr={err}")
    return proc


def _stop_daemon(socket_path: str) -> None:
    try:
        client_request(socket_path, {"op": "shutdown"})
    except Exception:
        pass
    # give time to shutdown
    time.sleep(0.1)


def test_vtermd_run_write_read_cycle():
    sock = ".x-vtermd-test.sock"
    proc = _start_daemon(sock)
    try:
        # run echo
        r1 = client_request(sock, {"op": "run", "cmd": "echo vterm"})
        assert r1["exit_code"] == 0
        assert any("vterm" in ln for ln in r1["lines"])  # type: ignore[index]

        # write a printf command to produce JSON then read
        text = "echo '{\"z\":3}'\n"
        client_request(sock, {"op": "write", "text": text})
        r2 = client_request(sock, {"op": "read", "timeout": 0.3})
        assert r2.get("json_objects"), r2
        assert r2["json_objects"][0]["z"] == 3  # type: ignore[index]
    finally:
        _stop_daemon(sock)
        proc.terminate()
        try:
            os.unlink(sock)
        except OSError:
            pass


@pytest.mark.live
def test_vtermd_with_claude_if_present():
    import shutil

    if shutil.which("claude") is None:
        pytest.skip("claude CLI not found; skipping live test")

    sock = ".x-vtermd-test.sock"
    proc = _start_daemon(sock, init_cmd="claude --dangersouly-skip-permissions")
    try:
        # Send a simple input such as 'help' and then read output
        client_request(sock, {"op": "write", "text": "help\n"})
        out = client_request(sock, {"op": "read", "timeout": 1.0})
        # We don't assert specific content; just require non-empty lines
        assert out["lines"] and isinstance(out["lines"], list)  # type: ignore[index]
    finally:
        _stop_daemon(sock)
        proc.terminate()
        try:
            os.unlink(sock)
        except OSError:
            pass
