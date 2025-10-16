# Selector Waits and Per-Action JSON Results (Oct 16, 2025)

## Wait Utilities
- `xbot/waits.py`: `wait_visible`, `wait_clickable`, `click_when_ready` for robust UI steps.
- Applied to reply/like/retweet/follow/unfollow/DM and compose flows.

## Per-Action Results
- `xbot/results.py`: writes `artifacts/results/<timestamp>_<action>.json` and `latest.json`.
- Each record includes success flag, meta, artifact paths (when present), and trace/HAR paths.

## Browser Paths
- `xbot/browser.py`: exposes `trace_path` and `har_path` properties for the active session.

## Validation
- Tests pass (skipping live). CLI help reflects health/queue groups.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo tree.

