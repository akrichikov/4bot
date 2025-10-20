from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_site_build_includes_secrets_scan(tmp_path: Path, monkeypatch):
    logs = tmp_path / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    (logs / 'sample.log').write_text('auth_token=abc123\n', encoding='utf-8')
    monkeypatch.setenv('LOGS_DIR', str(logs))
    out = tmp_path / 'status'
    r = CliRunner().invoke(app, ['site', 'build', '--out-dir', str(out)])
    assert r.exit_code == 0
    # secrets_scan.json created
    ss = out / 'secrets_scan.json'
    assert ss.exists()
    data = json.loads(ss.read_text(encoding='utf-8'))
    assert data['scanned_files'] >= 1
    # index includes link
    html = (out / 'index.html').read_text(encoding='utf-8')
    assert 'Secrets Scan (JSON)' in html
