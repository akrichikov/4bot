# Health Extensions and Profile Overrides (Oct 16, 2025)

## Health
- `health tweet-state --url <status>` shows `{liked, retweeted}`.
- `health compose` verifies presence of compose textbox and submit.

## Profiles and Overrides
- Named profiles map to `auth/<name>/storageState.json` and `.x-user/<name>/`.
- Optional per-profile overrides: `config/profiles/<name>.json` (e.g., `proxy_url`, `base_url`, `locale`).
- `PROFILE`/`X_PROFILE` envs set default profile; CLI `--profile` overrides.

## CI
- Uploads `artifacts/**` on CI test failures, aiding debugging.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo tree.

