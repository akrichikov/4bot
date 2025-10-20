from pathlib import Path
from xbot.report_health import write_status_index


def test_status_index_lists_markdown():
    outdir = Path('artifacts/test_outputs/status_index_md')
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'system_health.html').write_text('<html>health</html>', encoding='utf-8')
    (outdir / 'system_health.json').write_text('{"ok": true}', encoding='utf-8')
    (outdir / 'note.md').write_text('# Note', encoding='utf-8')
    idx = write_status_index(outdir)
    html = idx.read_text(encoding='utf-8')
    assert 'note.md' in html
