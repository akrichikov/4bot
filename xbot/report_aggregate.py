from __future__ import annotations

from typing import Any, Dict, Optional


def _health_summary(health: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not health:
        return {"present": False}
    cookies = health.get("cookies", {})
    storage = health.get("storage", {})
    vterm = health.get("vterm_http", {})
    rmq = health.get("rabbitmq", {})
    ok = (
        int(cookies.get("count", 0)) > 0
        and "auth_token" in set(cookies.get("keys_present", []))
        and bool(storage.get("exists"))
        and int(storage.get("cookie_count", 0)) > 0
        and bool(vterm.get("ok"))
        and bool(rmq.get("ok"))
    )
    return {
        "present": True,
        "ok": ok,
        "cookies": {"count": cookies.get("count", 0), "keys": cookies.get("keys_present", [])},
        "storage": {"exists": storage.get("exists", False), "cookie_count": storage.get("cookie_count", 0)},
        "vterm_http": {"ok": vterm.get("ok", False), "status": vterm.get("status", None)},
        "rabbitmq": {"ok": rmq.get("ok", False)},
    }


def _guard_summary(guard: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not guard:
        return {"present": False}
    summ = guard.get("summary", {})
    return {
        "present": True,
        "summary": {
            "PASS": int(summ.get("PASS", 0)),
            "EDIT": int(summ.get("EDIT", 0)),
            "BLOCK": int(summ.get("BLOCK", 0)),
        },
    }


def _sched_summary(sched: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not sched:
        return {"present": False}
    return {"present": True, "counts": sched.get("counts", {})}


def aggregate_status(
    health: Optional[Dict[str, Any]],
    guard: Optional[Dict[str, Any]],
    sched: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    h = _health_summary(health)
    g = _guard_summary(guard)
    s = _sched_summary(sched)
    return {"health": h, "guardrails": g, "scheduler": s}

