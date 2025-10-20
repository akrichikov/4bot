from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_report_gallery_cli(tmp_path: Path):
    src = tmp_path / "screens"
    src.mkdir(parents=True, exist_ok=True)
    # create dummy images (empty files are fine for link list)
    (src / "a.png").write_bytes(b"")
    (src / "b.jpg").write_bytes(b"")
    out = tmp_path / "status" / "screens_gallery.html"
    r = CliRunner().invoke(app, ["report", "gallery", "--src", str(src), "--out", str(out)])
    assert r.exit_code == 0
    html = out.read_text(encoding="utf-8")
    assert "a.png" in html and "b.jpg" in html
