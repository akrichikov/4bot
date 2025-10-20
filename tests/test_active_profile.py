from __future__ import annotations

from pathlib import Path

from xbot.config import Config


def test_honors_active_profile_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("PROFILE", raising=False)
    monkeypatch.delenv("X_PROFILE", raising=False)
    p = Path("config/active_profile")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("abc", encoding="utf-8")
    cfg = Config.from_env()
    assert cfg.profile_name == "abc"


def test_env_overrides_active_profile_file(tmp_path: Path, monkeypatch):
    p = Path("config/active_profile")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("abc", encoding="utf-8")
    monkeypatch.setenv("PROFILE", "zzz")
    cfg = Config.from_env()
    assert cfg.profile_name == "zzz"
