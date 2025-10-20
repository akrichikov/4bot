from __future__ import annotations

import json
import time
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_results_rebuild_index_cli(tmp_path: Path):
    res = tmp_path / 'results'
    res.mkdir(parents=True, exist_ok=True)
    # seed two minimal result jsons
    (res / 'a.json').write_text(json.dumps({"ts": 1700000000, "action": "alpha", "success": True}), encoding='utf-8')
    (res / 'b.json').write_text(json.dumps({"action": "beta"}), encoding='utf-8')
    out = res / 'index.jsonl'
    r = CliRunner().invoke(app, ['results', 'rebuild-index', '--src', str(res), '--out', str(out)])
    assert r.exit_code == 0
    lines = out.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 2
    recs = [json.loads(l) for l in lines]
    actions = {r['action'] for r in recs}
    assert actions == {'alpha', 'beta'}
