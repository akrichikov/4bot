from __future__ import annotations

import json
import os
import pty
import re
import shlex
import signal
import time
from dataclasses import dataclass
from select import select
from typing import Any, Dict, List, Optional, Tuple

import fcntl
import termios
import tty


@dataclass
class VTermResult:
    command: str
    exit_code: int
    raw_text: str
    lines: List[str]
    json_objects: List[Any]
    key_values: Dict[str, str]
    table: Optional[Dict[str, Any]]
    stats: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {
                "command": self.command,
                "exit_code": self.exit_code,
                "raw_text": self.raw_text,
                "lines": self.lines,
                "json_objects": self.json_objects,
                "key_values": self.key_values,
                "table": self.table,
                "stats": self.stats,
            }
        )


class VTerm:
    """
    In-memory virtual terminal (PTY) manager.

    - Launches an interactive shell inside a pseudo-terminal.
    - write(text): free-form write to the terminal.
    - run(command): executes a command and returns structured JSON extraction.
    - read_structured(): parses the last read raw buffer into structured JSON.
    - close(): terminates the shell process and releases PTY.
    """

    DONE_SENTINEL = "__VTERM_DONE__"

    def __init__(
        self,
        shell: Optional[str] = None,
        cols: int = 200,
        rows: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        # Prefer bash if available for consistent behavior, else fall back to $SHELL, then sh
        default_shell = "/bin/bash" if os.path.exists("/bin/bash") else os.environ.get("SHELL", "/bin/sh")
        self.shell = shell or default_shell
        self.cols = cols
        self.rows = rows
        self.env = {**os.environ, **(env or {})}
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self._buffer: bytearray = bytearray()

    # --------------------------- lifecycle ---------------------------
    def start(self) -> None:
        if self.master_fd is not None:
            return

        master_fd, slave_fd = pty.openpty()
        self.master_fd, self.slave_fd = master_fd, slave_fd

        # Configure window size
        self._set_winsize(self.rows, self.cols)

        # Non-blocking read on master
        fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # Spawn child shell attached to PTY
        pid = os.fork()
        if pid == 0:  # Child
            try:
                os.setsid()
                os.close(master_fd)
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)
                # Make terminal raw-ish
                tty.setraw(0)
                # Start interactive shell with a predictable prompt
                sh = self.shell
                args = [sh]
                # prefer interactive
                if os.path.basename(sh) in ("bash", "zsh", "fish", "sh"):
                    args.append("-i")
                # Set PS1 to reduce noise and enable sentinel detection
                self.env["PS1"] = "__VTERM__> "
                os.execvpe(args[0], args, self.env)
            except Exception:
                os._exit(1)
        else:  # Parent
            self.pid = pid
            os.close(slave_fd)
            # Drain initial banner if any
            self._drain(0.25)
            # normalize prompts and disable prompt commands
            self.write("export PS1='__VTERM__> '; export PS2=''; unset PROMPT_COMMAND 2>/dev/null || true\n")
            # Small settle time
            self._drain(0.05)

    def close(self) -> None:
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self.pid = None
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

    # ----------------------------- IO -------------------------------
    def write(self, text: str) -> None:
        if self.master_fd is None:
            raise RuntimeError("VTerm not started")
        os.write(self.master_fd, text.encode("utf-8", errors="ignore"))

    def run(self, command: str, timeout: float = 10.0) -> VTermResult:
        """
        Execute a single command and capture output until a sentinel arrives.
        Returns VTermResult with structured extraction.
        """
        self._ensure_started()
        start = time.time()
        sentinel = f"{self.DONE_SENTINEL}:"
        wrapper = f"( {command} ); printf '\n{sentinel}%s__\n' $?\n"
        self.write(wrapper)

        raw = self._read_until(lambda buf: sentinel.encode() in buf, timeout=timeout)
        elapsed = (time.time() - start) * 1000.0

        # Separate the sentinel footer
        exit_code = 0
        if sentinel in raw:
            before, after = raw.rsplit(sentinel, 1)
            # after like: "0__\n...prompt" — get integer prefix until underscore
            m = re.match(r"(\d+)__", after)
            if m:
                exit_code = int(m.group(1))
            raw = before

        return self._extract(command, raw, exit_code, elapsed)

    def read_structured(self, timeout: float = 0.1) -> VTermResult:
        """Read any available output and parse it into structured JSON fields."""
        self._ensure_started()
        chunk = self._drain(timeout)
        return self._extract("<read>", chunk, exit_code=0, elapsed=0.0)

    # --------------------------- internals --------------------------
    def _ensure_started(self) -> None:
        if self.master_fd is None:
            self.start()

    def _set_winsize(self, rows: int, cols: int) -> None:
        if self.slave_fd is None:
            return
        # TIOCSWINSZ expects rows, cols, xpix, ypix (shorts)
        import struct

        s = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.slave_fd, termios.TIOCSWINSZ, s)

    def _drain(self, max_wait: float) -> str:
        end = time.time() + max_wait
        out = bytearray()
        while time.time() < end:
            if self.master_fd is None:
                break
            r, _, _ = select([self.master_fd], [], [], 0.02)
            if not r:
                continue
            try:
                data = os.read(self.master_fd, 4096)
            except BlockingIOError:
                continue
            if not data:
                break
            out.extend(data)
        text = out.decode("utf-8", errors="replace")
        return text

    def _read_until(self, predicate, timeout: float) -> str:
        deadline = time.time() + timeout
        out = bytearray()
        while time.time() < deadline:
            if self.master_fd is None:
                break
            r, _, _ = select([self.master_fd], [], [], 0.05)
            if not r:
                continue
            try:
                data = os.read(self.master_fd, 4096)
            except BlockingIOError:
                continue
            if not data:
                break
            out.extend(data)
            if predicate(out):
                break
        return out.decode("utf-8", errors="replace")

    # ---------------------- structured extraction ------------------
    def _extract(
        self, command: str, raw_text: str, exit_code: int, elapsed: float
    ) -> VTermResult:
        # Normalize lines: drop prompt echoes
        # Strip ANSI and secondary prompts like "> >" that appear during heredocs/multiline
        cleaned_lines: List[str] = []
        for ln in raw_text.splitlines():
            if not ln.strip():
                continue
            s = self._strip_ansi(ln)
            # strip leading PS1 prompt if present
            if s.startswith("__VTERM__>"):
                s = s.split("__VTERM__>", 1)[1].lstrip()
            # remove leading groups of '>' and spaces typical of PS2
            s = re.sub(r"^(?:[> ]{1,4})+", "", s).rstrip()
            if s:
                cleaned_lines.append(s)
        lines = cleaned_lines

        json_objects: List[Any] = []
        key_values: Dict[str, str] = {}
        table: Optional[Dict[str, Any]] = None

        # 1) Try whole-text JSON
        obj = self._try_json(raw_text)
        if obj is not None:
            json_objects.append(obj)
        else:
            # 2) Try line-wise JSON
            for ln in lines:
                j = self._try_json(ln)
                if j is not None:
                    json_objects.append(j)

        # 3) Key/Value pairs (k=v or k: v)
        for ln in lines:
            m = re.match(r"^\s*([^:=\s][^:=]*?)\s*[:=]\s*(.+)\s*$", ln)
            if m:
                key, val = m.group(1).strip(), m.group(2).strip()
                if key and val:
                    key_values[key] = val

        # 4) Simple table detection (space-separated columns)
        if not json_objects:
            if len(lines) >= 2:
                headers = self._split_cols(lines[0])
                rows: List[List[str]] = []
                if len(headers) >= 2:
                    for ln in lines[1:]:
                        cols = self._split_cols(ln)
                        if len(cols) == len(headers):
                            rows.append(cols)
                if rows:
                    table = {
                        "headers": headers,
                        "rows": [dict(zip(headers, r)) for r in rows],
                    }

        stats = {
            "bytes": len(raw_text.encode("utf-8", errors="ignore")),
            "lines": len(lines),
            "elapsed_ms": round(elapsed, 3),
        }

        return VTermResult(
            command=command,
            exit_code=exit_code,
            raw_text=raw_text,
            lines=lines,
            json_objects=json_objects,
            key_values=key_values,
            table=table,
            stats=stats,
        )

    @staticmethod
    def _try_json(text: str) -> Optional[Any]:
        s = text.strip()
        if not s:
            return None
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return None
        return None

    @staticmethod
    def _split_cols(line: str) -> List[str]:
        # Split by 2+ spaces to preserve fields containing single spaces
        parts = re.split(r"\s{2,}", line.strip())
        return [p for p in parts if p]

    @staticmethod
    def _strip_ansi(s: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*[mK]", "", s)


__all__ = ["VTerm", "VTermResult"]
