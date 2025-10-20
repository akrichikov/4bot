from __future__ import annotations

import os
import time
from pathlib import Path
from typer.testing import CliRunner

from xbot.cli import app


def test_results_prune_deletes_old_files(tmp_path: Path):
    out = tmp_path / "results"
    out.mkdir(parents=True, exist_ok=True)
    old = out / "20200101_old.json"
    old.write_text("{}", encoding="utf-8")
    pinned1 = out / "index.jsonl"; pinned1.write_text("{}\n", encoding="utf-8")
    pinned2 = out / "latest.json"; pinned2.write_text("{}", encoding="utf-8")
    pinned3 = out / "report.html"; pinned3.write_text("<html></html>", encoding="utf-8")
    # set old mtime
    long_ago = time.time() - 90*86400
    os.utime(old, (long_ago, long_ago))

    r = CliRunner().invoke(app, ["results", "prune", "--days", "1", "--out-dir", str(out)])
    assert r.exit_code == 0
    assert not old.exists()
    # pinned preserved
    assert pinned1.exists() and pinned2.exists() and pinned3.exists()
