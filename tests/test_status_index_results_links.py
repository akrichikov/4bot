from pathlib import Path
from xbot.report_health import write_status_index


def test_status_index_includes_results_proxies():
    outdir = Path('artifacts/test_outputs/status_index_results')
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'system_health.html').write_text('<html>health</html>', encoding='utf-8')
    (outdir / 'system_health.json').write_text('{"ok": true}', encoding='utf-8')
    # seed proxies
    (outdir / 'results_report.html').write_text('<html>proxy</html>', encoding='utf-8')
    (outdir / 'daily_index.html').write_text('<html>proxy</html>', encoding='utf-8')
    idx = write_status_index(outdir)
    html = idx.read_text(encoding='utf-8')
    assert 'Results Report' in html and 'results_report.html' in html
    assert 'Daily Reports' in html and 'daily_index.html' in html
