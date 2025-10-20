from pathlib import Path
from xbot.report_health import write_status_index


def test_status_index_prioritizes_paths_artifacts():
    outdir = Path('artifacts/test_outputs/status_index_paths')
    outdir.mkdir(parents=True, exist_ok=True)
    # Seed health
    (outdir / 'system_health.html').write_text('<html>health</html>', encoding='utf-8')
    (outdir / 'system_health.json').write_text('{"ok": true}', encoding='utf-8')
    # Seed paths artifacts
    (outdir / 'paths.md').write_text('# Paths', encoding='utf-8')
    (outdir / 'paths.json').write_text('{"x":1}', encoding='utf-8')
    (outdir / 'paths_doctor.json').write_text('{"ok":true}', encoding='utf-8')
    (outdir / 'paths_env.json').write_text('{"PROFILE":"default"}', encoding='utf-8')
    (outdir / 'repo_layout.md').write_text('# Layout', encoding='utf-8')
    (outdir / 'status_summary.json').write_text('{"summary":{}}', encoding='utf-8')

    idx = write_status_index(outdir)
    html = idx.read_text(encoding='utf-8')
    assert 'Paths Summary (MD)' in html
    assert 'Paths (JSON)' in html
    assert 'Paths Doctor (JSON)' in html
    assert 'Paths Env (JSON)' in html
    assert 'Repo Layout (MD)' in html
    assert 'Status Summary (JSON)' in html
