# 2025-10-18 Repository Reorg Applied

## Commands Executed

- `pwd && ls && tree -a -L 2` (tree used as t fallback)
- `pytest -q` to validate zero integration regressions

## New Top-Level Layout (condensed)

- `xbot/` core package (unchanged)
- `apps/` app entrypoints (unchanged)
- `scripts/`
  - `auth/`, `launch/`, `manual/`, `monitor/`, `notification/`, `orchestrator/`, `rabbitmq/`
  - `shell/` moved all `.sh` launchers and dashboards here
- `bin/launchd/` LaunchAgents `.plist` files
- `config/monitor/monitor_config.json` (moved from root)
- `artifacts/`
  - `results/` JSON results (intercepted posts, ai_posts_intercepted.json)
  - `screens/` screenshots (auth/profile verification)
  - `state/` runtime state (replied_mentions.json)
  - `misc/` stray markers (`=1.3`, `3.9`, `package-lock.json`)
- `logs/` consolidated logs and `.out`
- `Docs/` documentation and status reports

## Path Updates (upstream/downstream)

- `scripts/shell/launch_cz_daemon.sh` now copies `bin/launchd/com.4botbsc.cz-daemon.plist`
- `scripts/shell/status_dashboard.sh` reads `artifacts/state/replied_mentions.json`
- `scripts/monitor/monitor_mentions.py` stores state at `artifacts/state/replied_mentions.json` and reads auth `config/profiles/4botbsc/storageState.json`
- `scripts/monitor/generate_health_report.py` reads `artifacts/state/replied_mentions.json`
- `scripts/notification/verify_posts.py` writes screenshot to `artifacts/screens/profile_verification.png`
- `scripts/monitor/headless_monitor.py` logs under `logs/monitor/` and writes results to `artifacts/results/`
- `scripts/manual/manual_event_monitor.py` logs to `logs/event_monitor.log`
- `Makefile` `start-all`/`stop-all` -> `scripts/shell/launch_complete_pipeline.sh`

## Requirements and Ignore

- Added `requirements.txt` (unpinned major deps + dev)
- `.gitignore` now ignores `logs/` in addition to `artifacts/`

## Validation

- Tests: 1 skipped (live), all others pass. No errors/failures.
- Root now contains no `.sh`, `.plist`, `.json`, `.log`, `.png`, `=1.3`, or `3.9` files.

## Notes

- Docs referencing legacy paths remain for historical trace, but current scripts use new paths. Use this report as the single source of truth for file locations.
