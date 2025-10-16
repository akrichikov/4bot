# Cookie Bootstrap & Session Utilities (Oct 16, 2025)

## Summary
- Added storage state import/export and session check.
- Browser applies storage state on launch and exports on exit.

## New Commands
- `python -m xbot.cli cookies export --path auth/storageState.json`
- `python -m xbot.cli cookies import --path auth/storageState.json`
- `python -m xbot.cli session check`
- `python -m xbot.cli follow https://x.com/<handle>`
- `python -m xbot.cli unfollow https://x.com/<handle>`
- `python -m xbot.cli dm https://x.com/<handle> "message text"`

## Implementation
- `xbot/state.py`: `apply_storage_state`, `export_storage_state`.
- `xbot/browser.py`: applies storage state at enter; exports at exit.
- `xbot/cli.py`: added `cookies` and `session` subcommands.

## Notes
- Prefer cookie-based auth to minimize UI logins.
- Update `xbot/selectors.py` if X UI changes.

## Violations Check
- No backups; no `/tmp/**`; tree-confined changes only.
