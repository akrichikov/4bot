Title: Shell Launchers Absolute-Path Scrub and Launchd Templates
Date: 2025-10-18

Summary
- Replaced hard-coded /Users/* paths in shell launchers with repo-relative resolution.
- Kept feature parity; no behavioral changes expected.
- Added Docs/launchd/* templated plists with placeholders.
- Augmented .gitignore to exclude generated Docs/status HTML/JSON.

Changed files
- scripts/shell/run_cz_batch_replies.sh → dynamic REPO_ROOT + module launch.
- scripts/shell/launch_4bot.sh → dynamic REPO_ROOT; fixed script targets.
- scripts/shell/launch_cz_daemon.sh → dynamic REPO_ROOT.
- scripts/shell/start_headless_replies.sh → dynamic REPO_ROOT.
- scripts/shell/start_cz_daemon.sh → dynamic REPO_ROOT.
- scripts/shell/launch_complete_pipeline.sh → dynamic SCRIPT_DIR.
- Docs/launchd/*.template.plist → new templates.
- .gitignore → ignore Docs/status generated files.

Acceptance checks
- rg '/Users/' shows only in non-code artifacts (docs/configs/plists under bin). Templates now provided under Docs/launchd.
- pytest collection passes under .venv.
