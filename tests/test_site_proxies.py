from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_site_build_writes_result_proxies(tmp_path: Path):
    # Prepare a fake results report and daily index under default location
    res = Path('artifacts/results')
    (res).mkdir(parents=True, exist_ok=True)
    (res / 'report.html').write_text('<html>rep</html>', encoding='utf-8')
    (res / 'daily').mkdir(parents=True, exist_ok=True)
    (res / 'daily' / 'index.html').write_text('<html>daily</html>', encoding='utf-8')

    out = tmp_path / 'site_proxy'
    r = CliRunner().invoke(app, ["site", "build", "--out-dir", str(out)])
    assert r.exit_code == 0
    # Proxies should exist
    rp = (out / 'results_report.html').read_text(encoding='utf-8')
    dp = (out / 'daily_index.html').read_text(encoding='utf-8')
    assert 'Results Report' in rp and '../artifacts/results/report.html' in rp
    assert 'Daily Reports' in dp and '../artifacts/results/daily/index.html' in dp
