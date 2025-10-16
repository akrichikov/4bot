# Compose Retries and Proxy Check (Oct 16, 2025)

## Compose
- Added `COMPOSE_OPENERS` and `ensure_composer()` to open the modal if textbox not visible.
- Compose now selects a visible textbox among fallbacks and clicks any visible submit.

## State-Aware Actions
- Like/Retweet now wait for state markers (`UNLIKE_BUTTON`, `UNRETWEET_BUTTON`) after click.

## Profiles
- Sample overlay: `config/profiles/sample.json` (proxy/locale/timezone/viewport).
- `profile proxy-check [name]` loads the profile and fetches a public IP/headers endpoint.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo tree.

