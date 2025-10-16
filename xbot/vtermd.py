from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .vterm import VTerm


DEFAULT_SOCKET = ".x-vterm.sock"


def _recv_line(conn: socket.socket) -> Optional[str]:
    buf = bytearray()
    while True:
        data = conn.recv(4096)
        if not data:
            return None if not buf else buf.decode("utf-8", errors="replace")
        buf.extend(data)
        if b"\n" in data:
            break
    return buf.decode("utf-8", errors="replace")


def _send_json(conn: socket.socket, obj: Dict[str, Any]) -> None:
    data = (json.dumps(obj) + "\n").encode("utf-8")
    conn.sendall(data)


@dataclass
class VTermDaemon:
    socket_path: str = DEFAULT_SOCKET
    init_cmd: Optional[str] = None

    def __post_init__(self) -> None:
        self.vt = VTerm()
        self._server: Optional[socket.socket] = None
        self._stop = threading.Event()

    def serve(self) -> None:
        # Clean any stale socket
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        self.vt.start()
        if self.init_cmd:
            try:
                # Avoid sentinel wait for interactive programs; send as write
                self.vt.write(self.init_cmd + "\n")
                # Drain any immediate output
                self.vt.read_structured(timeout=0.2)
            except Exception:
                pass

        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.socket_path)
        srv.listen(5)
        self._server = srv

        # Main accept loop
        while not self._stop.is_set():
            try:
                srv.settimeout(0.5)
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()

        try:
            srv.close()
        finally:
            self._server = None
            self.vt.close()
            try:
                if os.path.exists(self.socket_path):
                    os.unlink(self.socket_path)
            except OSError:
                pass

    def _handle_conn(self, conn: socket.socket) -> None:
        with conn:
            line = _recv_line(conn)
            if not line:
                return
            try:
                req = json.loads(line.strip())
            except Exception as e:
                _send_json(conn, {"error": f"invalid json: {e}"})
                return

            try:
                op = req.get("op")
                if op == "run":
                    cmd = req.get("cmd", "")
                    timeout = float(req.get("timeout", 10.0))
                    res = self.vt.run(str(cmd), timeout=timeout)
                    _send_json(conn, json.loads(res.to_json()))
                elif op == "write":
                    text = str(req.get("text", ""))
                    self.vt.write(text)
                    _send_json(conn, {"ok": True, "wrote": len(text)})
                elif op == "read":
                    timeout = float(req.get("timeout", 0.1))
                    res = self.vt.read_structured(timeout=timeout)
                    _send_json(conn, json.loads(res.to_json()))
                elif op == "shutdown":
                    self._stop.set()
                    _send_json(conn, {"ok": True, "shutdown": True})
                else:
                    _send_json(conn, {"error": f"unknown op: {op}"})
            except Exception as e:
                _send_json(conn, {"error": str(e)})


def client_request(socket_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.connect(socket_path)
    try:
        _send_json(conn, payload)
        resp = _recv_line(conn)
        if not resp:
            raise RuntimeError("no response")
        return json.loads(resp)
    finally:
        conn.close()

