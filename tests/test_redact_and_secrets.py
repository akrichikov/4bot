from __future__ import annotations

import os
from pathlib import Path

from xbot.utils import redact
from xbot import secrets


def test_redact_keeps_prefix_suffix_and_hash():
    out = redact("abcdefghij", hint="test")
    # Expect 'abc…ij [sha256:test:XXXXXXXX]'
    assert out.startswith("abc…ij [sha256:test:"), out
    assert len(out.split(":")[-1].rstrip("]")) == 8


def test_secrets_file_backend(tmp_path: Path, monkeypatch):
    sec = tmp_path / "secrets.json"
    monkeypatch.setenv("XBOT_SECRETS_FILE", str(sec))
    secrets.set("token", "VALUE123")
    assert secrets.get("token") == "VALUE123"
    assert sec.exists()
    assert secrets.delete("token") is True
    assert secrets.get("token") is None

