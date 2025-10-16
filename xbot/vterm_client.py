from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

from .vtermd import client_request as unix_request


@dataclass
class VTermClient:
    mode: str  # 'http' or 'unix'
    base: str | None = None  # e.g., http://127.0.0.1:9876
    socket_path: str | None = None  # e.g., .x-vterm.sock
    token: str | None = None  # shared secret for HTTP

    async def run_http(self, cmd: str, timeout: float = 10.0) -> Dict[str, Any]:
        assert self.base, "base required for http mode"
        async with aiohttp.ClientSession(headers=(
            {"X-VTerm-Token": self.token} if self.token else None
        )) as sess:
            async with sess.post(f"{self.base}/run", json={"cmd": cmd, "timeout": timeout}) as r:
                return await r.json()

    async def write_http(self, text: str) -> Dict[str, Any]:
        assert self.base, "base required for http mode"
        async with aiohttp.ClientSession(headers=(
            {"X-VTerm-Token": self.token} if self.token else None
        )) as sess:
            async with sess.post(f"{self.base}/write", json={"text": text}) as r:
                return await r.json()

    async def read_http(self, timeout: float = 0.2) -> Dict[str, Any]:
        assert self.base, "base required for http mode"
        async with aiohttp.ClientSession(headers=(
            {"X-VTerm-Token": self.token} if self.token else None
        )) as sess:
            async with sess.get(f"{self.base}/read", params={"timeout": str(timeout)}) as r:
                return await r.json()

    def run_unix(self, cmd: str, timeout: float = 10.0) -> Dict[str, Any]:
        assert self.socket_path, "socket_path required for unix mode"
        return unix_request(self.socket_path, {"op": "run", "cmd": cmd, "timeout": timeout})

    def write_unix(self, text: str) -> Dict[str, Any]:
        assert self.socket_path, "socket_path required for unix mode"
        return unix_request(self.socket_path, {"op": "write", "text": text})

    def read_unix(self, timeout: float = 0.2) -> Dict[str, Any]:
        assert self.socket_path, "socket_path required for unix mode"
        return unix_request(self.socket_path, {"op": "read", "timeout": timeout})

