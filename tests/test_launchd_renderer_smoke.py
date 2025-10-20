from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from scripts.launch.install_launchd_from_templates import app


def test_launchd_renderer_dry_run(tmp_path: Path):
    tpls = tmp_path / "Docs/launchd"
    tpls.mkdir(parents=True, exist_ok=True)
    # Minimal template using variables; ensure no absolute /Users/ literal is required here
    (tpls / "com.sample.template.plist").write_text(
        """<plist><dict><key>WorkingDirectory</key><string>${REPO_ROOT}</string></dict></plist>""",
        encoding="utf-8",
    )
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "render",
            "--templates-dir",
            str(tpls),
            "--out-dir",
            str(tmp_path / "bin/launchd"),
            "--var",
            "REPO_ROOT=/opt/repo",
            "--var",
            "LOG_DIR=/opt/repo/logs",
            "--dry-run",
        ],
    )
    assert res.exit_code == 0
