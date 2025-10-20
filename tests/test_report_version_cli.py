from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_report_version_cli(tmp_path: Path):
    out = tmp_path / 'version.json'
    r = CliRunner().invoke(app, ['report','version','--out', str(out)])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding='utf-8'))
    assert 'timestamp' in data and 'python_version' in data and 'project_version' in data
