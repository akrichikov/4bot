# 2025-10-18 CP – Wrapper Hygiene and Root Residual Guards

## Context
After the repository reorganization and deduplication, we need guardrails to:
- Keep root-level hygiene (no *.sh, *.plist, *.json, *.log, *.png, or marker files like =1.3, 3.9 at repo base).
- Ensure notification wrappers stay thin shims that delegate to the canonical `xbot.notification_json_parser` implementation.
- Preserve zero behavior changes and green test suite.

## Objectives
- Add automated tests that fail on regressions in root hygiene.
- Add automated tests that fail if wrapper scripts accrete canonical logic (schemas/classes/functions) again.
- Capture operator transcript and reorg summary for traceability.

## Embedded Transcript/Status (Operator Inputs)

- Explored └ Search \breplied_mentions\.json\b
- Ran echo 'Root residuals check:' && ls -1 *.sh *.plist *.json *.log *.png 2>/dev/null || echo 'OK: none' && [ -e =1.3 ] && echo 'FOUND =1.3' || echo 'OK: no =1.3' && [ -e 3.9 ] && echo 'FOUND 3.9' || │ echo 'OK: no 3.9'
└ Root residuals check: OK: none OK: no =1.3 OK: no 3.9
─ Worked for 11m 12s

• Proceeding with a safe, in-place repo reorg and path refactors. I ran the mapping and validated no regressions.

Command Outputs
- pwd: /Users/doctordre/projects/4bot
- ls: cleaned; no .sh, .plist, .json, .log, .png, =1.3, 3.9 at repo root
- t: not found; used tree -a -L 2 instead. Root summary: 73 directories, 179 files

New Hierarchy (multi-level)
- xbot/ (core package; unchanged)
- apps/ (app entrypoints; unchanged)
- scripts/
  - auth/, launch/, manual/, monitor/, notification/, orchestrator/, rabbitmq/
  - shell/ moved all top-level .sh: cleanup_orphans.sh, launch_4bot.sh, launch_complete_pipeline.sh, launch_cz_daemon.sh, launch_tweet_replies.sh, run_cz_batch_replies.sh, start_cz_daemon.sh, start_headless_replies.sh, status_dashboard.sh
- bin/launchd/ moved .plist: com.4botbsc.cz-daemon.plist, com.4botbsc.vterm-http.plist
- config/
  - monitor/ monitor_config.json (moved from root)
  - profiles/ (as before)
- artifacts/
  - results/ ai_posts_intercepted.json, intercepted_posts_*.json (moved from root)
  - screens/ auth_verification.png, profile_verification.png (moved from root)
  - state/ replied_mentions.json (moved from root)
  - misc/ =1.3, 3.9, package-lock.json (moved from root)
- logs/ consolidated: event_monitor.log, monitor_log_*.log, notification_parser.log, test_monitor_output.log, auto_responder.out, vterm_http.out, cz_posts.out, etc.
- Docs/ (unchanged; status reports updated)

Refactors and Dependency Updates
- Makefile
  - start-all → scripts/shell/launch_complete_pipeline.sh start
  - stop-all → scripts/shell/launch_complete_pipeline.sh stop
- scripts/shell/launch_cz_daemon.sh – Copies bin/launchd/com.4botbsc.cz-daemon.plist to ~/Library/LaunchAgents
- scripts/shell/status_dashboard.sh – Reads artifacts/state/replied_mentions.json
- scripts/monitor/monitor_mentions.py – storage_path → config/profiles/4botbsc/storageState.json; replied_tweets_file → artifacts/state/replied_mentions.json (auto-creates dir)
- scripts/monitor/generate_health_report.py – Reads artifacts/state/replied_mentions.json
- scripts/notification/verify_posts.py – Saves screenshot to artifacts/screens/profile_verification.png (auto-creates dir)
- scripts/monitor/headless_monitor.py – Logs to logs/monitor/headless_<ts>.log; writes results to artifacts/results
- scripts/manual/manual_event_monitor.py – Logs to logs/event_monitor.log (auto-creates dir)

Requirements and Ignore
- Added requirements.txt (unpinned; latest packages)
  - playwright, pydantic, python-dotenv, typer, rich, tenacity, pyotp, aiohttp, pycryptodome, pytest, pytest-asyncio, ruff, black, pika
- .gitignore – Ensures logs/ is ignored (artifacts/ already ignored)

Validation
- Pytest collection: OK
- Full test run: s................................................................ [100%]
- Root residual check:
  - No .sh, .plist, .json, .log, .png files at repo base
  - No =1.3 or 3.9 at repo base

Identified Paths (moved)
- Shell: scripts/shell/*.sh
- LaunchAgents: bin/launchd/*.plist
- Monitor config: config/monitor/monitor_config.json
- Runtime state: artifacts/state/replied_mentions.json
- Results: artifacts/results/*
- Screenshots: artifacts/screens/*
- Logs/outs: logs/*

Violation Absence Confirmation
- 0 shell/plist/json/log/png files left at repo root
- 0 marker files (=1.3, 3.9) left at repo root
- All operations confined to tree-mapped paths; no duplicates introduced

Post-Execution Tree (excerpt)
- scripts/shell/, bin/launchd/, config/monitor/, artifacts/{results,screens,state,misc}, logs/ present and populated as above.

Notes
- Historical docs still reference prior root paths; current single source-of-truth is this reorg. Status change recorded in Docs/status/2025-10-18_repo_reorg_applied.md.

## Tasks
1. Add test_repo_hygiene: assert no banned file patterns or marker files exist at repo base.
2. Add test_wrapper_hygiene for notification wrappers:
   - Must import canonical `xbot.notification_json_parser`.
   - Must not define canonical classes/schemas (e.g., ParsedNotification, NotificationMetrics, PostContent).
   - Must compile without syntax errors.
3. Run full pytest and confirm no regressions.
4. Update this status on success.

## Acceptance Criteria
- All tests pass (existing + new).
- Any reintroduction of banned root files or wrapper duplication fails CI.

## Risks & Mitigations
- False positives on wrapper content: choose conservative forbidden tokens (canonical class names) and allow import of canonical module.
- Avoid scanning subdirectories in root hygiene test to prevent false alarms; restrict to repo base.

