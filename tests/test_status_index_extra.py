from pathlib import Path
from xbot.report_health import write_status_index


def test_status_index_lists_other_artifacts():
    outdir = Path('artifacts/test_outputs/status_index_extra')
    outdir.mkdir(parents=True, exist_ok=True)
    # seed health first
    (outdir / 'system_health.html').write_text('<html>health</html>', encoding='utf-8')
    (outdir / 'system_health.json').write_text('{"ok": true}', encoding='utf-8')
    # seed some other files
    (outdir / 'alpha.html').write_text('<html>a</html>', encoding='utf-8')
    (outdir / 'beta.json').write_text('{"b": 1}', encoding='utf-8')
    (outdir / 'index.html').write_text('<html>old</html>', encoding='utf-8')  # should be ignored

    idx = write_status_index(outdir)
    html = idx.read_text(encoding='utf-8')
    # prioritized
    assert 'System Health (HTML)' in html and 'system_health.html' in html
    assert 'System Health (JSON)' in html and 'system_health.json' in html
    # others
    assert 'alpha.html' in html
    assert 'beta.json' in html
    # not listing index.html itself
    assert html.count('index.html') == 0
