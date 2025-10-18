Title: DRY Refactor – Deduplications Across New Hierarchy
Date: 2025-10-18

Input Analysis
- Duplicate CZ reply generators: apps/cz/vterm_request_proxy_manager.py and apps/cz/cz_batch_reply.py.
- Parallel notification parsers: xbot/notification_json_parser.py (canonical) and scripts/notification/notification_json_parser.py and working_notification_json_parser.py.
- Mixed absolute path inserts previously addressed; verified none remain.

Synthesis
- Create shared module `xbot/cz_reply.py` exporting `CZReplyGenerator` (templates + heuristics union of prior versions).
- Refactor CZ call sites to import the shared generator.
- Convert both CLI parsers under scripts/notification to thin wrappers that delegate to `xbot.notification_json_parser.NotificationJSONParser`.
- Keep script entry points intact while eliminating core logic duplication.

Output
- New: xbot/cz_reply.py (single source of truth for CZ template replies).
- apps/cz/vterm_request_proxy_manager.py: now imports shared generator; legacy class renamed internally (not used by runtime path).
- apps/cz/cz_batch_reply.py: uses `CZBatchResponder` wrapper over shared generator.
- scripts/notification/notification_json_parser.py and working_notification_json_parser.py: thin wrappers invoking canonical xbot implementation.

Verification
- Commands executed:
  - pwd && ls (root) to confirm structure after prior reorg.
  - tree scan with ignore filters to map hierarchy.
  - ripgrep to locate duplicates and imports.
  - pytest -q: all tests pass (1 skip), no new warnings.

Blind Spot & Gap Check
- No remaining absolute project-root sys.path insertions.
- Launchers updated earlier to module form; no further changes required here.

Violation Absence Confirmation
- No backups created; no /tmp usage introduced; no duplicate modules remain for CZ replies or notification parser logic.

Next Steps
- Optional: add CLI entry points in pyproject for `cz-proxy`, `cz-daemon`, and `xbot-notifications` to simplify invocation (`python -m` already works).
