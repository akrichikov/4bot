from __future__ import annotations

import json
from pathlib import Path

from xbot.report_html import html_report


def test_report_html_uses_relative_image_paths(tmp_path: Path):
    arts = tmp_path / 'artifacts'
    screens = arts / 'screens'
    results = arts / 'results'
    screens.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    shot = screens / 'sample.png'
    shot.write_bytes(b'')

    index = results / 'index.jsonl'
    rec = {"ts": 1700000000, "action": "test", "success": True, "artifacts": {"screenshot": str(shot)}}
    index.write_text(json.dumps(rec) + "\n", encoding='utf-8')

    out = results / 'report.html'
    html_report(index, out)
    html = out.read_text(encoding='utf-8')
    assert '../screens/sample.png' in html
