Title: Critical Path Follow-up – Imports, Launchers, Warnings
Date: 2025-10-18

Summary
- Removed hard-coded sys.path absolute paths; added dynamic root resolution or switched to module execution (-m).
- Updated launchers to run modules: apps.cz.* via python -m for reliable imports.
- Fixed SyntaxWarning hot spots by switching JavaScript snippets to raw strings (r"""...").
- Adjusted JS extractor paths after reorg.
- Re-ran full tests: green, no warnings.

Changes
- apps/cz/*: replaced absolute sys.path inserts with dynamic guard; retained direct execution compatibility.
- xbot/cli.py and apps/cz/cz_vterm_rabbitmq_daemon.py: JS eval strings now raw to avoid invalid escape warnings.
- apps/cz/cz_vterm_rabbitmq_daemon.py and scripts/notification/notification_json_parser.py: point to scripts/notification/enhanced_notification_extractor.js.
- launch_complete_pipeline.sh: now runs managers with `python3 -m`, writes test script under artifacts/tmp (no /tmp), and uses dynamic repo root in that script.
- launch_cz_daemon.sh: updated to `python3 -m apps.cz.cz_vterm_rabbitmq_daemon`.

Verification
- pytest -q: all tests pass, no warnings.
- grep for absolute sys.path inserts: none remaining for project root.

Notes
- LaunchAgent plist retains WorkingDirectory and PYTHONPATH; path was updated to new location and remains functional.
