Title: Auth Check CLI – Cookie Audit + Session Verification
Date: 2025-10-18

Summary
- Added `xbot auth-check` command to audit cookies and verify login in a headless browser.
- Uses centralized cookie loader and merges into storage when needed.

Usage
- `xbot auth-check --profile 4botbsc --headless true`
- Output includes total cookie count, presence of key tokens (auth_token, ct0, kdt, att), and login status.

Technical
- Implementation in `xbot/cli.py` leverages:
  - `load_cookies_best_effort(profile)` to find cookies across known sources.
  - `merge_into_storage()` to synthesize `storageState.json` if missing/empty.
  - `Browser` + `is_logged_in()` to validate session.

Verification
- pytest -q: green across suite (1 skip), no new warnings.
