from __future__ import annotations

import html
import json
from datetime import datetime, date
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def load_index(index_path: Path) -> List[Dict[str, Any]]:
    if not index_path.exists():
        return []
    recs: List[Dict[str, Any]] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            continue
    return recs


def fmt_ts(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts).isoformat(sep=" ", timespec="seconds")
    except Exception:
        return str(ts)


def html_report(
    index_path: Path,
    out_path: Path,
    actions: Optional[List[str]] = None,
    limit: int = 100,
    date_str: Optional[str] = None,
) -> Path:
    recs = load_index(index_path)
    if actions:
        want = set(a.lower() for a in actions)
        recs = [r for r in recs if str(r.get("action", "")).lower() in want]
    # filter by date if specified (YYYY-MM-DD)
    if date_str:
        tmp: List[Dict[str, Any]] = []
        for r in recs:
            ts = int(r.get("ts", 0) or 0)
            d = datetime.fromtimestamp(ts).date().isoformat()
            if d == date_str:
                tmp.append(r)
        recs = tmp
    recs = recs[-limit:]

    parts: List[str] = []
    parts.append("<html><head><meta charset='utf-8'>")
    parts.append(
        "<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;padding:16px} .ok{color:#0a0}.fail{color:#a00} code{background:#f6f8fa;padding:2px 4px;border-radius:3px} .card{border:1px solid #ddd;border-radius:6px;padding:12px;margin:8px 0} .muted{color:#666;font-size:12px} .chip{border:1px solid #ccc;border-radius:12px;padding:4px 8px;background:#fff;cursor:pointer;margin-right:6px}</style>"
    )
    parts.append("</head><body>")
    parts.append("<h1>XBot Report</h1>")
    # link to daily index if exists
    daily = out_path.parent / "daily"
    if daily.exists():
        parts.append(f"<div><a href='{html.escape(str((Path('daily') / '').as_posix()))}'>Daily reports</a></div>")
    parts.append(f"<div class='muted'>Index: {html.escape(str(index_path))}</div>")

    if not recs:
        parts.append("<p>No results.</p>")
    else:
        # derive available action filters and top summary
        actions_set = sorted({str(r.get('action','')) for r in recs})
        # Top summary table
        counts = {}
        oks = {}
        for r in recs:
            a = str(r.get('action',''))
            counts[a] = counts.get(a,0)+1
            if r.get('success'): oks[a] = oks.get(a,0)+1
        parts.append("<h2>Summary</h2><table><tr><th>Action</th><th>Count</th><th>OK</th><th>Rate</th></tr>")
        for a in actions_set:
            c = counts.get(a,0); o = oks.get(a,0); rate = (o/c*100 if c else 0)
            parts.append(f"<tr><td>{html.escape(a)}</td><td>{c}</td><td>{o}</td><td>{rate:.1f}%</td></tr>")
        parts.append("</table>")

        parts.append("<div style='margin:8px 0'>Filter: ")
        for a in actions_set:
            parts.append(f"<button class='chip' data-chip='{html.escape(a)}' onclick=\"filterAction('{html.escape(a)}')\">{html.escape(a)}</button> ")
        parts.append("<button class='chip' onclick=\"filterAction('')\">All</button></div>")

        parts.append("<div style='margin:8px 0'>Show failures only: <button class='chip' onclick=\"filterFailures()\">Failures</button></div>")
        for r in recs[::-1]:
            ok = bool(r.get("success"))
            action = html.escape(str(r.get("action")))
            ts = fmt_ts(int(r.get("ts", 0)))
            meta = r.get("meta", {}) or {}
            artifacts = r.get("artifacts", {}) or {}
            trace = r.get("trace")
            har = r.get("har")
            parts.append(f"<div class='card' data-action='{action}' data-ok='{1 if ok else 0}'>")
            parts.append(f"<div><strong>{action}</strong> <span class='{ 'ok' if ok else 'fail' }'>{'OK' if ok else 'FAIL'}</span></div>")
            parts.append(f"<div class='muted'>{ts}</div>")
            if meta:
                parts.append("<details><summary>Meta</summary><pre>")
                parts.append(html.escape(json.dumps(meta, ensure_ascii=False, indent=2)))
                parts.append("</pre></details>")
            # Inline screenshot thumbnail if present
            thumb = None
            if isinstance(artifacts, dict) and "screenshot" in artifacts:
                thumb = artifacts.get("screenshot")
            if thumb:
                try:
                    tpath = Path(str(thumb))
                    rel = os.path.relpath(tpath, out_path.parent)
                except Exception:
                    rel = str(thumb)
                parts.append(f"<div><img src='{html.escape(rel)}' alt='screenshot' style='max-width:300px;border:1px solid #ccc;border-radius:4px' /></div>")
            # direct link if status_id present in meta
            status_id = meta.get('status_id') if isinstance(meta, dict) else None
            if status_id:
                parts.append(f"<div>status: <a href='https://x.com/i/web/status/{html.escape(str(status_id))}' target='_blank'>open</a></div>")
            if artifacts or trace or har:
                parts.append("<details><summary>Artifacts</summary>")
                if artifacts:
                    for k, v in artifacts.items():
                        parts.append(f"<div>{html.escape(k)}: <code>{html.escape(str(v))}</code></div>")
                if trace:
                    parts.append(f"<div>trace: <code>{html.escape(str(trace))}</code></div>")
                if har:
                    parts.append(f"<div>har: <code>{html.escape(str(har))}</code></div>")
                parts.append("</details>")
            parts.append("</div>")

    parts.append("<script>function filterAction(a){document.querySelectorAll('.card').forEach(function(el){var v=!a||el.getAttribute('data-action')===a; el.style.display=v?'block':'none';});} function filterFailures(){document.querySelectorAll('.card').forEach(function(el){var v=el.getAttribute('data-ok')==='0'; el.style.display=v?'block':'none';});}</script>")
    parts.append("</body></html>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path


def _summaries_by_day(index_path: Path) -> Dict[str, Dict[str, Any]]:
    recs = load_index(index_path)
    days: Dict[str, Dict[str, Any]] = {}
    for r in recs:
        ts = int(r.get("ts", 0) or 0)
        d = datetime.fromtimestamp(ts).date().isoformat()
        day = days.setdefault(d, {"total": 0, "ok": 0, "by_action": {}})
        day["total"] += 1
        if r.get("success"):
            day["ok"] += 1
        a = str(r.get("action", ""))
        ba = day["by_action"].setdefault(a, {"count": 0, "ok": 0})
        ba["count"] += 1
        if r.get("success"):
            ba["ok"] += 1
    return days


def daily_index(outdir: Path) -> Path:
    daily = outdir / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    # Ensure per-day reports exist for days present in index.jsonl
    sums = _summaries_by_day(outdir / "index.jsonl")
    for day in list(sums.keys()):
        page = daily / f"{day}.html"
        if not page.exists():
            try:
                html_report(outdir / "index.jsonl", page, date_str=day)
            except Exception:
                # ignore generation errors; day will simply be skipped
                pass
    items = sorted(daily.glob("*.html"))

    html_parts: List[str] = []
    html_parts.append("<html><head><meta charset='utf-8'><title>Daily Reports</title>")
    html_parts.append("<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;padding:16px} a{color:#06c;text-decoration:none} table{border-collapse:collapse} td,th{border:1px solid #ddd;padding:6px} th{background:#f6f8fa}</style>")
    html_parts.append("</head><body><h1>Daily Reports</h1>")
    # Summary table
    html_parts.append("<h2>Summary</h2><table><tr><th>Day</th><th>Total</th><th>Success</th><th>Rate</th><th>Actions</th></tr>")
    for p in items[::-1]:
        day = p.stem
        s = sums.get(day, {"total": 0, "ok": 0, "by_action": {}})
        total = s.get("total", 0)
        ok = s.get("ok", 0)
        rate = (ok/total*100 if total else 0)
        # build compact actions string
        acts = s.get("by_action", {})
        act_str = ", ".join([f"{html.escape(a)}: {v.get('ok',0)}/{v.get('count',0)}" for a,v in acts.items()])
        html_parts.append(f"<tr><td><a href='{p.name}'>{day}</a></td><td>{total}</td><td>{ok}</td><td>{rate:.1f}%</td><td>{act_str}</td></tr>")
    html_parts.append("</table>")
    html_parts.append("</body></html>")
    index_path = daily / "index.html"
    index_path.write_text("\n".join(html_parts), encoding="utf-8")
    return index_path
