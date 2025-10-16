from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import threading
import os

from aiohttp import web

from .vterm import VTerm
from pathlib import Path as _Path
from collections import deque
from math import inf


class _TokenBucket:
    def __init__(self, rate_qps: float, burst: int) -> None:
        self.rate = float(rate_qps)
        self.burst = int(burst)
        self.tokens: float = float(burst)
        self.last = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class VTermHTTPServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: str | None = None,
        admin_token: str | None = None,
        rate_qps: Optional[float] = None,
        rate_burst: int = 5,
        audit_log: Optional[Path] = None,
        audit_enabled: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.vt = VTerm()
        self.rate_qps = rate_qps
        self.rate_burst = rate_burst
        self.audit_log = audit_log
        self.audit_enabled = audit_enabled
        self.admin_token = admin_token
        self._buckets: dict[str, _TokenBucket] = {}
        self.app = web.Application()
        self._metrics = {
            "requests_total": 0,
            "auth_fail_total": 0,
            "rate_limited_total": 0,
        }
        from collections import defaultdict as _dd
        self._metrics_by_path = _dd(int)
        self._run_exit_codes = _dd(int)
        self._run_hist = {
            "buckets": [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, inf],
            "counts": {0.05: 0, 0.1: 0, 0.25: 0, 0.5: 0, 1.0: 0, 2.0: 0, 5.0: 0, inf: 0},
            "sum": 0.0,
            "cnt": 0,
        }
        self._events: deque[Dict[str, Any]] = deque(maxlen=200)
        self.app.add_routes(
            [
                web.get("/health", self.health),
                web.get("/console", self.console),
                web.get("/static/{name}", self.static_file),
                web.get("/metrics", self.metrics),
                web.post("/run", self.run_cmd),
                web.post("/write", self.write_text),
                web.get("/read", self.read_structured),
                web.get("/tail", self.tail),
                web.get("/ws", self.ws_stream),
                web.post("/admin/shutdown", self.admin_shutdown),
                web.post("/queue/run", self.queue_run),
                web.get("/queue", self.queue_list),
                web.get("/queue/{job_id}", self.queue_get),
            ]
        )
        # serialize run() operations to avoid interleaving
        self._run_lock = asyncio.Lock()
        self._jobs: dict[int, dict] = {}
        self._job_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._job_counter = 0
        self.app.on_startup.append(self._startup)
        self.app.on_cleanup.append(self._cleanup)

    def _auth(self, request: web.Request) -> bool:
        self._metrics["requests_total"] += 1
        self._metrics_by_path[request.path] += 1
        if not self.token:
            return True
        hdr = request.headers.get("X-VTerm-Token") or request.query.get("token")
        ok = hdr == self.token
        if not ok:
            self._metrics["auth_fail_total"] += 1
        return ok

    def _key(self, request: web.Request) -> str:
        # prefer token, else peername addr
        tok = request.headers.get("X-VTerm-Token") or request.query.get("token") or ""
        if tok:
            return f"tok:{tok}"
        peer = request.transport.get_extra_info("peername") if request.transport else None
        ip = None
        if isinstance(peer, tuple) and len(peer) >= 1:
            ip = peer[0]
        return f"ip:{ip or 'unknown'}"

    def _ratelimit(self, request: web.Request) -> Optional[Tuple[int, Dict[str, Any]]]:
        if self.rate_qps is None:
            return None
        key = self._key(request)
        b = self._buckets.get(key)
        if b is None:
            b = _TokenBucket(self.rate_qps, self.rate_burst)
            self._buckets[key] = b
        if not b.allow():
            return 429, {"error": "rate_limited"}
        return None

    def _audit(self, record: Dict[str, Any]) -> None:
        if not self.audit_enabled or not self.audit_log:
            return
        try:
            p = Path(self.audit_log)
            p.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record}, ensure_ascii=False)
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # best-effort; ignore audit errors
            pass

    async def health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def run_cmd(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            self._audit({"path": "/run", "auth": False})
            return web.json_response({"error": "unauthorized"}, status=401)
        rl = self._ratelimit(request)
        if rl:
            code, payload = rl
            self._audit({"path": "/run", "rate_limited": True})
            return web.json_response(payload, status=code)
        payload: Dict[str, Any] = await request.json()
        cmd = str(payload.get("cmd", ""))
        timeout = float(payload.get("timeout", 10.0))
        if not cmd:
            return web.json_response({"error": "missing cmd"}, status=400)
        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()
        async with self._run_lock:
            res = await loop.run_in_executor(None, lambda: self.vt.run(cmd, timeout=timeout))
        dur = max(0.0, time.perf_counter() - t0)
        data = json.loads(res.to_json())
        self._audit({"path": "/run", "auth": True, "cmd": cmd, "exit_code": data.get("exit_code")})
        try:
            self._run_exit_codes[str(data.get("exit_code"))] += 1
        except Exception:
            pass
        # observe histogram
        try:
            self._run_hist["sum"] += dur
            self._run_hist["cnt"] += 1
            for b in self._run_hist["buckets"]:
                if dur <= b:
                    self._run_hist["counts"][b] += 1
                    break
        except Exception:
            pass
        try:
            self._events.append({"type": "run", **data})
        except Exception:
            pass
        return web.json_response(data)

    async def console(self, request: web.Request) -> web.StreamResponse:
        # Serve embedded static console
        root = _Path(__file__).resolve().parent / "static"
        f = root / "vterm_console.html"
        return web.FileResponse(path=str(f))

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        name = (request.match_info.get("name") or "").strip("/..")
        root = _Path(__file__).resolve().parent / "static"
        path = root / name
        if not path.exists():
            raise web.HTTPNotFound()
        return web.FileResponse(path=str(path))

    async def metrics(self, request: web.Request) -> web.Response:
        lines = []
        m = self._metrics
        lines.append(f"vterm_requests_total {m.get('requests_total',0)}")
        lines.append(f"vterm_auth_fail_total {m.get('auth_fail_total',0)}")
        lines.append(f"vterm_rate_limited_total {m.get('rate_limited_total',0)}")
        for p, c in sorted(self._metrics_by_path.items()):
            path = p.replace('"','\"')
            lines.append(f'vterm_requests_by_path{{path="{path}"}} {c}')
        for ec, c in sorted(self._run_exit_codes.items()):
            lines.append(f'vterm_run_exit_codes{{code="{ec}"}} {c}')
        # histogram exposition
        hist = self._run_hist
        for b in hist["buckets"]:
            le = "+Inf" if b is inf else ("%.2f" % b).rstrip('0').rstrip('.')
            lines.append(f'vterm_run_duration_seconds_bucket{{le="{le}"}} {hist["counts"].get(b,0)}')
        lines.append(f'vterm_run_duration_seconds_sum {hist["sum"]}')
        lines.append(f'vterm_run_duration_seconds_count {hist["cnt"]}')
        body = "\n".join(lines) + "\n"
        return web.Response(text=body, content_type="text/plain; version=0.0.4")

    async def admin_shutdown(self, request: web.Request) -> web.Response:
        # Require explicit admin token distinct from normal token when provided
        tok = request.headers.get("X-VTerm-Admin") or request.query.get("admin")
        if self.admin_token and tok != self.admin_token:
            return web.json_response({"error": "unauthorized"}, status=401)
        # Respond OK, then terminate process shortly after
        def _exit():
            try:
                self.vt.close()
            finally:
                os._exit(0)
        threading.Timer(0.15, _exit).start()
        return web.json_response({"ok": True, "shutting_down": True})

    async def _startup(self, app: web.Application) -> None:
        self._worker_task = asyncio.create_task(self._job_worker())

    async def _cleanup(self, app: web.Application) -> None:
        try:
            self._worker_task.cancel()  # type: ignore[attr-defined]
        except Exception:
            pass
        await asyncio.sleep(0)

    # --------------- queue API -----------------
    async def queue_run(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        payload: Dict[str, Any] = await request.json()
        cmd = str(payload.get("cmd", ""))
        timeout = float(payload.get("timeout", 10.0))
        if not cmd:
            return web.json_response({"error": "missing cmd"}, status=400)
        self._job_counter += 1
        jid = self._job_counter
        job = {"id": jid, "cmd": cmd, "timeout": timeout, "status": "pending", "result": None}
        self._jobs[jid] = job
        await self._job_queue.put(job)
        return web.json_response({"job_id": jid, "status": job["status"]})

    async def queue_list(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        jobs = list(sorted(self._jobs.values(), key=lambda j: j["id"], reverse=True))[:50]
        return web.json_response({"jobs": [{k: v for k, v in j.items() if k != "result"} for j in jobs]})

    async def queue_get(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        try:
            jid = int(request.match_info.get("job_id") or "0")
        except Exception:
            return web.json_response({"error": "invalid id"}, status=400)
        job = self._jobs.get(jid)
        if not job:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"id": job["id"], "status": job["status"], "result": job.get("result")})

    async def _job_worker(self) -> None:
        while True:
            job = await self._job_queue.get()
            job["status"] = "running"
            try:
                loop = asyncio.get_running_loop()
                async with self._run_lock:
                    res = await loop.run_in_executor(None, lambda: self.vt.run(job["cmd"], timeout=job["timeout"]))
                data = json.loads(res.to_json())
                job["result"] = data
                job["status"] = "done"
                try:
                    self._events.append({"type": "run", **data})
                except Exception:
                    pass
            except Exception as e:
                job["status"] = "error"
                job["result"] = {"error": str(e)}
            finally:
                self._job_queue.task_done()

    async def write_text(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            self._audit({"path": "/write", "auth": False})
            return web.json_response({"error": "unauthorized"}, status=401)
        rl = self._ratelimit(request)
        if rl:
            code, payload = rl
            self._audit({"path": "/write", "rate_limited": True})
            return web.json_response(payload, status=code)
        payload: Dict[str, Any] = await request.json()
        text = str(payload.get("text", ""))
        self.vt.write(text)
        self._audit({"path": "/write", "auth": True, "bytes": len(text)})
        try:
            self._events.append({"type": "write", "text": text})
        except Exception:
            pass
        return web.json_response({"ok": True, "wrote": len(text)})

    async def read_structured(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            self._audit({"path": "/read", "auth": False})
            return web.json_response({"error": "unauthorized"}, status=401)
        rl = self._ratelimit(request)
        if rl:
            code, payload = rl
            self._audit({"path": "/read", "rate_limited": True})
            return web.json_response(payload, status=code)
        try:
            timeout = float(request.query.get("timeout", "0.2"))
        except Exception:
            timeout = 0.2
        res = self.vt.read_structured(timeout=timeout)
        data = json.loads(res.to_json())
        self._audit({"path": "/read", "auth": True, "lines": len(data.get("lines", []))})
        try:
            self._events.append({"type": "read", **data})
        except Exception:
            pass
        return web.json_response(data)

    async def tail(self, request: web.Request) -> web.Response:
        if not self._auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        try:
            limit = int(request.query.get("limit", "10"))
        except Exception:
            limit = 10
        limit = max(1, min(limit, len(self._events)))
        data = list(self._events)[-limit:]
        return web.json_response({"events": data})

    async def ws_stream(self, request: web.Request) -> web.WebSocketResponse:
        if not self._auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        ws = web.WebSocketResponse(heartbeat=20.0)
        await ws.prepare(request)
        last_sent_bytes = 0
        # optional replay of last N events
        try:
            replay = int(request.query.get("replay", "0"))
        except Exception:
            replay = 0
        if replay > 0 and self._events:
            for evt in list(self._events)[-min(replay, len(self._events)):]:
                await ws.send_str(json.dumps(evt))
        try:
            while True:
                res = self.vt.read_structured(timeout=0.2)
                data = json.loads(res.to_json())
                # Only send when there is meaningful content
                raw = data.get("raw_text", "")
                has_payload = bool(data.get("lines") or data.get("json_objects") or data.get("key_values") or raw.strip())
                if has_payload:
                    last_sent_bytes += len(raw.encode("utf-8", errors="ignore"))
                    packed = {"type": "read", **data}
                    self._events.append(packed)
                    await ws.send_str(json.dumps(packed))
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        finally:
            await ws.close()
        return ws

    def run(self) -> None:
        try:
            self.vt.start()
            web.run_app(self.app, host=self.host, port=self.port, handle_signals=False)
        finally:
            self.vt.close()
