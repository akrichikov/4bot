from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def _badge(ok: bool) -> str:
    return f"<span style='padding:2px 8px;border-radius:12px;color:#fff;background:{'#0a0' if ok else '#a00'}'>{'OK' if ok else 'FAIL'}</span>"


def write_system_health_html(
    report: Dict[str, Any],
    out_path: Path,
    guard: Optional[Dict[str, Any]] = None,
    sched: Optional[Dict[str, Any]] = None,
) -> Path:
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

    # Guardrails (optional)
    if guard:
        parts.append("<div class='card'>")
        parts.append("<h2>Guardrails</h2>")
        summ = (guard.get("summary") or {})
        p = int(summ.get("PASS", 0)); e = int(summ.get("EDIT", 0)); b = int(summ.get("BLOCK", 0))
        parts.append(f"<div>PASS: <strong>{p}</strong> &nbsp; EDIT: <strong>{e}</strong> &nbsp; BLOCK: <strong>{b}</strong></div>")
        parts.append("</div>")

    # Scheduler (optional)
    if sched:
        parts.append("<div class='card'>")
        parts.append("<h2>Scheduler</h2>")
        counts = (sched.get("counts") or sched.get("processed") or {})
        if counts:
            parts.append("<ul>")
            for name in sorted(counts.keys()):
                parts.append(f"<li>{html.escape(str(name))}: <strong>{int(counts[name])}</strong></li>")
            parts.append("</ul>")
        else:
            parts.append("<div>No scheduler results found.</div>")
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


def write_status_index(outdir: Path) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    idx = outdir / "index.html"

    # Discover known artifacts
    health_html = outdir / "system_health.html"
    health_json = outdir / "system_health.json"

    # Prioritized links
    links: list[tuple[str, Path]] = []
    if health_html.exists():
        links.append(("System Health (HTML)", health_html))
    if health_json.exists():
        links.append(("System Health (JSON)", health_json))

    # Enumerate other HTML/JSON artifacts in the same directory (non-recursive)
    others: list[Path] = []
    for p in sorted(outdir.glob("*.html")):
        if p.name not in {"index.html", "system_health.html"}:
            others.append(p)
    for p in sorted(outdir.glob("*.json")):
        if p.name not in {"system_health.json"}:
            others.append(p)

    parts: list[str] = []
    parts.append("<html><head><meta charset='utf-8'><title>Status Index</title>")
    parts.append("<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;padding:16px} li{margin:6px 0}</style>")
    parts.append("</head><body>")
    parts.append("<h1>Status Index</h1>")
    parts.append("<ul>")
    if links:
        for label, p in links:
            rel = p.name
            parts.append(f"<li><a href='{html.escape(rel)}'>{html.escape(label)}</a></li>")
    # add a separator between prioritized health links and others
    if links and others:
        parts.append("</ul><h2>Other Artifacts</h2><ul>")
    for p in others:
        parts.append(f"<li><a href='{html.escape(p.name)}'>{html.escape(p.name)}</a></li>")
    if not links and not others:
        parts.append("<li><em>No known status artifacts yet.</em></li>")
    parts.append("</ul>")
    parts.append("</body></html>")

    idx.write_text("\n".join(parts), encoding="utf-8")
    return idx
