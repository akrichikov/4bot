from pathlib import Path
from xbot.report_health import write_status_index


def test_write_status_index_artifacts(tmp_path_factory):
    # Use a directory under artifacts to avoid /tmp policy concerns
    outdir = Path('artifacts/test_outputs/status_index')
    (outdir).mkdir(parents=True, exist_ok=True)
    # seed fake health files
    (outdir / 'system_health.html').write_text('<html>ok</html>', encoding='utf-8')
    (outdir / 'system_health.json').write_text('{"ok": true}', encoding='utf-8')
    idx = write_status_index(outdir)
    html = idx.read_text(encoding='utf-8')
    assert 'system_health.html' in html
    assert 'system_health.json' in html

