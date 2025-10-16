# Cookie Bootstrap and Idempotent Actions (Oct 16, 2025)

## Cookie Bootstrap
- New command: `python -m xbot.cli cookies merge-json <src.json> [--dest auth/storageState.json] [--filter-domain x.com]`.
- Accepts Playwright `storageState` format or Chrome export lists; normalizes and merges.
- Filters to `x.com`/`twitter.com` domains by default; merges by (name, domain, path).

## Idempotent Actions
- Like/Retweet now check current state:
  - If `unlike`/`unretweet` is present, skip clicking to avoid toggling off.
  - After clicking, waits for the expected state using robust waits.

## Selector Fallbacks
- Added state markers: `UNLIKE_BUTTON`, `UNRETWEET_BUTTON`.
- Compose/selectors widened earlier remain in effect.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo.

