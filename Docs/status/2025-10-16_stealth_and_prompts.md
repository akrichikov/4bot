# Stealth/Env Controls and Media Editor Prompts (Oct 16, 2025)

## Stealth/Env (config)
- `LOCALE`, `TIMEZONE_ID`, `USER_AGENT`, `VIEWPORT_WIDTH`, `VIEWPORT_HEIGHT`
- Optional geolocation: `GEO_LAT`, `GEO_LON`, `GRANT_GEOLOCATION`
- Applied to both persistent and non-persistent contexts.

## Media Editor Prompts
- `xbot/prompts.py`: detects Done/Close buttons in media editor and dismisses if present.
- Integrated into post-media flow after previews appear.

## Selector/Wait Enhancements
- Fallback compose/submit selectors and any-visible click/waits.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo.

