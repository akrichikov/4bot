Title: Repository Reorganization – Zero Python Files at Repo Root
Date: 2025-10-18

Summary
- Consolidated Python sources into structured subpackages and scripts folders.
- Updated imports, tests, and launch scripts accordingly.
- Verified: 0 Python files remain in repo root; test suite passes.

Command Outputs
- PWD/LS baseline: /Users/doctordre/projects/4bot (captured before changes).
- pytest (after changes): all tests pass with 1 skip; no errors.
- Sanity: `ls -1 *.py` at repo root → no results.

Moves (selected highlights)
- Core messaging: `rabbitmq_manager.py` → `xbot/rabbitmq_manager.py`.
- Notification parser: `final_notification_json_parser.py` → `xbot/notification_json_parser.py`.
- CZ apps: `cz_*.py`, `vterm_cz_integration.py`, `vterm_request_proxy_manager.py` → `apps/cz/`.
- Auth scripts: cookie/login utilities → `scripts/auth/`.
- Monitoring: monitors/health/report tools → `scripts/monitor/`.
- Notifications: monitors/parsers/validators → `scripts/notification/`.
- RabbitMQ tools: setup/test → `scripts/rabbitmq/`.
- Orchestrator/launchers/manuals → `scripts/orchestrator/`, `scripts/launch/`, `scripts/manual/`.

Code/Config Updates
- Tests updated to import from `xbot.rabbitmq_manager` and `xbot.notification_json_parser`.
- CLI now imports CZ daemon from `apps.cz.cz_vterm_rabbitmq_daemon` (added `apps/__init__.py`, `apps/cz/__init__.py`).
- Launch scripts and LaunchAgent plist point to new paths under `apps/cz/`.

Identified Paths (post-change top-level)
- Packages: `xbot/`, `apps/cz/`.
- Scripts: `scripts/auth/`, `scripts/monitor/`, `scripts/notification/`, `scripts/rabbitmq/`, `scripts/orchestrator/`, `scripts/launch/`, `scripts/manual/`.
- Data/Config: `auth/`, `auth_data/`, `config/`, `artifacts/`, `logs/`, `Docs/`, `playbooks/`, `schedules/`, `prompts/`.

Violation Check
- No backups created; no duplicates introduced.
- No usage of /tmp storage for code (only transient test snippet in launcher retained, unrelated to package imports).
- All operations confined to tree‑mapped paths under repo.

Verification
- Re-ran `pytest -q` → green.
- CLI smoke via tests invoking `python -m xbot.cli` continues to work.

Notes
- Two SyntaxWarning notices remain in JS regex literals within Python strings; non-blocking and unchanged behavior.
