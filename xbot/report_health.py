from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _badge(ok: bool) -> str:
    return f"<span style='padding:2px 8px;border-radius:12px;color:#fff;background:{'#0a0' if ok else '#a00'}'>{'OK' if ok else 'FAIL'}</span>"


def write_system_health_html(report: Dict[str, Any], out_path: Path) -> Path:
    parts: list[str] = []
    parts.append("<html><head><meta charset='utf-8'><title>System Health</title>")
    parts.append(
        "<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;padding:16px} .card{border:1px solid #ddd;border-radius:8px;padding:12px;margin:10px 0} h2{margin:8px 0} code{background:#f6f8fa;padding:2px 4px;border-radius:3px}</style>"
    )
    parts.append("</head><body>")
    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    parts.append(f"<h1>System Health <span class='muted' style='color:#666;font-size:12px'>Generated {html.escape(ts)}</span></h1>")

    # Cookies
    c = report.get("cookies", {})
    parts.append("<div class='card'>")
    parts.append("<h2>Cookies</h2>")
    parts.append(f"<div>Count: <strong>{int(c.get('count',0))}</strong></div>")
    kp = c.get("keys_present") or []
    parts.append(f"<div>Keys: <code>{html.escape(', '.join(kp))}</code></div>")
    parts.append("</div>")

    # Storage
    s = report.get("storage", {})
    parts.append("<div class='card'>")
    parts.append("<h2>Storage</h2>")
    parts.append(f"<div>Path: <code>{html.escape(str(s.get('path','')))}</code></div>")
    parts.append(f"<div>Exists: {'Yes' if s.get('exists') else 'No'}</div>")
    parts.append(f"<div>Cookie Count: {int(s.get('cookie_count',0))}</div>")
    if s.get("error"):
        parts.append(f"<div style='color:#a00'>Error: {html.escape(str(s.get('error')))}</div>")
    parts.append("</div>")

    # VTerm HTTP
    v = report.get("vterm_http", {})
    parts.append("<div class='card'>")
    parts.append("<h2>VTerm HTTP</h2>")
    ok = bool(v.get("ok"))
    parts.append(f"<div>Base: <code>{html.escape(str(v.get('base','')))}</code> {_badge(ok)}</div>")
    parts.append(f"<div>Status: {html.escape(str(v.get('status','')))}; Latency: {html.escape(str(v.get('latency_ms','')))} ms</div>")
    if v.get("error"):
        parts.append(f"<div style='color:#a00'>Error: {html.escape(str(v.get('error')))}</div>")
    parts.append("</div>")

    # RabbitMQ
    r = report.get("rabbitmq", {})
    parts.append("<div class='card'>")
    parts.append("<h2>RabbitMQ</h2>")
    rok = bool(r.get("ok"))
    parts.append(f"<div>Connection: {_badge(rok)}</div>")
    if r.get("error"):
        parts.append(f"<div style='color:#a00'>Error: {html.escape(str(r.get('error')))}</div>")
    parts.append("</div>")

    # Raw JSON
    parts.append("<div class='card'>")
    parts.append("<h2>Raw JSON</h2>")
    parts.append("<pre>")
    parts.append(html.escape(json.dumps(report, ensure_ascii=False, indent=2)))
    parts.append("</pre></div>")

    parts.append("</body></html>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path

