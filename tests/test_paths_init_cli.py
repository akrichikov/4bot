from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_paths_init_creates_subdirs(tmp_path: Path, monkeypatch):
    # Override roots to a temporary location
    arts = tmp_path / "arts"
    logs = tmp_path / "logs"
    monkeypatch.setenv("ARTIFACTS_DIR", str(arts))
    monkeypatch.setenv("LOGS_DIR", str(logs))

    r = CliRunner().invoke(app, ["paths", "init"])
    assert r.exit_code == 0
    for sub in ["results", "screens", "html", "traces", "har", "state", "secure", "misc"]:
        assert (arts / sub).exists()
    for sub in ["monitor", "cz_daemon", "headless_batch"]:
        assert (logs / sub).exists()
