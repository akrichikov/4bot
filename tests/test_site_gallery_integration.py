from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_site_build_includes_screens_gallery(tmp_path: Path, monkeypatch):
    arts = tmp_path / 'artifacts'
    screens = arts / 'screens'
    screens.mkdir(parents=True, exist_ok=True)
    (screens / 'a.png').write_bytes(b'')
    monkeypatch.setenv('ARTIFACTS_DIR', str(arts))
    out = tmp_path / 'status'
    r = CliRunner().invoke(app, ['site', 'build', '--out-dir', str(out)])
    assert r.exit_code == 0
    sg = out / 'screens_gallery.html'
    assert sg.exists()
    html = (out / 'index.html').read_text(encoding='utf-8')
    assert 'Screens Gallery (HTML)' in html
