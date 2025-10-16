# Reliability, Human-like Interaction, and Observability (Oct 16, 2025)

## Summary
- Added retries/jitter utilities and human-like typing.
- Enabled HAR capture (non-persistent contexts) and JSONL action logging.
- Handle-based profile URL resolution for follow/unfollow/dm.

## Config (env)
- `RETRY_ATTEMPTS`, `JITTER_MIN_MS`, `JITTER_MAX_MS`
- `HUMANIZE`, `TYPE_MIN_MS`, `TYPE_MAX_MS`
- `TRACE_ENABLED`, `TRACE_DIR`, `SLOW_MO_MS`
- `HAR_ENABLED`, `HAR_DIR`

## Key Files
- `xbot/utils.py` (jitter, with_retries)
- `xbot/human.py` (type_text)
- `xbot/telemetry.py` (JsonLogger with async action context)
- `xbot/browser.py` (HAR in new_context, tracing)
- `xbot/flows/login.py` (humanized typing, small jitter)
- `xbot/facade.py` (humanized compose/reply/DM, handle→URL)

## Notes
- HAR capture applies on non-persistent contexts only (Playwright API limitation).
- Update selectors in `xbot/selectors.py` if X UI changes.

## Violations Check
- No backups; no `/tmp/**`; changes confined to mapped tree.

