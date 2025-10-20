from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from xbot.cli import app


def test_cli_profile_info_and_doctor(tmp_path: Path, monkeypatch):
    # Prepare a temporary profile with storageState
    prof = "clitest"
    storage = Path("config/profiles") / prof / "storageState.json"
    storage.parent.mkdir(parents=True, exist_ok=True)
    storage.write_text('{"cookies": [{"name": "ct0", "value": "abc"}]}', encoding="utf-8")
    # Ensure user data dir exists for doctor() to pass
    udir = Path(".x-user") / prof
    udir.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    res1 = runner.invoke(app, ["profile", "info", prof])
    assert res1.exit_code == 0
    assert str(storage) in res1.stdout

    res2 = runner.invoke(app, ["profile", "doctor", prof])
    assert res2.exit_code == 0
    assert "'ok': True" in res2.stdout or '"ok": true' in res2.stdout

    # Now set-default and verify active_profile is written and read
    res3 = runner.invoke(app, ["profile", "set-default", prof])
    assert res3.exit_code == 0
    ap = Path("config/active_profile")
    assert ap.exists() and ap.read_text(encoding="utf-8").strip() == prof
    from xbot.config import Config
    cfg = Config.from_env()
    assert cfg.profile_name == prof
