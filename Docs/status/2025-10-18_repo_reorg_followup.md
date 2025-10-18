# 2025-10-18 Repo Reorg Follow-up – Audit, Fixes, Verification

## Command Outputs
- CWD: `/Users/doctordre/projects/4bot`
- Root listing: cleaned; no banned file types in repo root
- Snapshot (depth=2): 73 directories, 179 files

```
$ pwd && ls -la | head -n 20
/Users/doctordre/projects/4bot
...

$ (command -v tree >/dev/null 2>&1 && tree -a -L 2) || echo 'tree unavailable'
73 directories, 179 files

$ bash -lc "ls -1 *.sh *.plist *.json *.log *.png 2>/dev/null || echo 'OK: none'"
OK: none
```

## Identified Paths (moved/normalized)
- `scripts/shell/*.sh` – all launch scripts
- `bin/launchd/*.plist` – launchd plists
- `config/monitor/monitor_config.json`
- `artifacts/state/replied_mentions.json`
- `artifacts/results/*` – results JSON
- `artifacts/screens/*` – screenshots
- `logs/**/*` – consolidated logs

## Changes in this pass
- Deduplication cleanup:
  - `scripts/notification/notification_json_parser.py` – trimmed to a thin wrapper around `xbot.notification_json_parser` (removed stale appended code).
  - `apps/cz/cz_batch_reply.py` – fixed `CZBatchResponder` to delegate to shared `CZReplyGenerator` (removed recursion bug).

## Dependencies & Tooling
- venv active (Python shown by local env). `requirements.txt` remains unpinned as desired.
- `.gitignore` already covers `artifacts/`, `logs/`, `.venv/`, etc.

## Tests
- `pytest -q`: `s................................................................` (1 skip, rest pass).

## Violations – None
- Root has zero: `*.sh`, `*.plist`, `*.json`, `*.log`, `*.png`.
- Root has no markers: `=1.3`, `3.9`.

## Next Steps (high level)
- Sweep remaining scripts to ensure path helpers are used consistently (`xbot.profiles`, `xbot.cookies`, `xbot.config`).
- Optional: add CLI entries exposed in `pyproject.toml` for wrappers (already added for key tools).

