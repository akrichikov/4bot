Title: CLI Entrypoints and Centralized Paths
Date: 2025-10-18

Summary
- Added executable CLIs via pyproject:
  - `cz-proxy` → apps.cz.vterm_request_proxy_manager:main
  - `cz-daemon` → apps.cz.cz_vterm_rabbitmq_daemon:main
  - `xbot-notifications` → xbot.notification_json_parser:main
- Centralized directories in xbot.config:
  - artifacts_dir, logs_dir, notification_log_dir (env-overridable: ARTIFACTS_DIR, LOGS_DIR, NOTIFICATION_LOG_DIR)
- xbot.notification_json_parser now uses Config.notification_log_dir.
- Tests re-run: green.

Usage
- `pip install -e .` then run: `cz-proxy`, `cz-daemon`, or `xbot-notifications --duration 120`.

Notes
- Backwards compatibility preserved (`python -m apps.cz.*` still works).
