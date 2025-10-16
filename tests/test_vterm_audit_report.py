from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from xbot.cli import app
from xbot.audit_report import summarize_vterm_audit, render_vterm_audit_html


def test_vterm_audit_summary_and_cli(tmp_path: Path):
    log = tmp_path / "vterm_audit.jsonl"
    # write sample events
    events = [
        {"ts":"2025-10-16T00:00:00Z","path":"/run","auth":True,"cmd":"echo A","exit_code":0},
        {"ts":"2025-10-16T00:00:01Z","path":"/run","auth":True,"cmd":"echo A","exit_code":0},
        {"ts":"2025-10-16T00:00:02Z","path":"/run","auth":True,"cmd":"echo B","exit_code":1},
        {"ts":"2025-10-16T00:00:03Z","path":"/write","auth":True,"bytes":10},
        {"ts":"2025-10-16T00:00:04Z","path":"/read","auth":False},
        {"ts":"2025-10-16T00:00:05Z","path":"/run","auth":True,"cmd":"echo C","exit_code":0},
        {"ts":"2025-10-16T00:00:06Z","path":"/run","rate_limited":True},
    ]
    log.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

    summary = summarize_vterm_audit(log)
    assert summary["total"] == len(events)
    assert summary["auth_fail"] == 1
    assert summary["rate_limited"] == 1
    assert summary["exit_codes"].get("0") == 3
    assert summary["by_path"]["/run"] == 5

    html = render_vterm_audit_html(summary)
    assert "VTerm Audit Report" in html and "Top Commands" in html

    runner = CliRunner()
    out_html = tmp_path / "report.html"
    out_json = tmp_path / "summary.json"
    res = runner.invoke(app, ["report", "vterm-audit", "--log", str(log), "--out-html", str(out_html), "--out-json", str(out_json)])
    assert res.exit_code == 0, res.output
    assert out_html.exists() and out_json.exists()

