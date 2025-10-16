# Python Playwright Scaffold (Oct 16, 2025)

## Command Outputs (summarized)
- Created `.venv` and installed: `playwright, pydantic, python-dotenv, typer, rich, tenacity, pytest`.
- Ran `python -m playwright install chromium` to provision browser.

## Added/Updated Paths
- `pyproject.toml` (console script `xbot`)
- `xbot/` package: `__init__.py`, `config.py`, `browser.py`, `flows/login.py`, `facade.py`, `cli.py`
- `tests/test_collect_only.py` (live env sanity)
- `.gitignore` additions: `.venv/`, Playwright state dirs

## Removed (entropy reduction)
- `package.json`, `tsconfig.json`, `.eslintrc.json`, `src/`, `bin/`, `node_modules/`, `dist/` (Node scaffold removed per switch to Python)

## Usage
1. Create `.env` with:
   - `X_USER`, `X_PASSWORD` (and optionally `X_EMAIL`, `X_2FA_CODE`)
   - `HEADLESS=true`, `PERSIST_SESSION=true`, `STORAGE_STATE=auth/storageState.json`, `USER_DATA_DIR=.x-user`
2. Activate venv and run login:
   - `source .venv/bin/activate`
   - `xbot login`
3. Post / reply / like / retweet / media / follow / DM:
   - `xbot post --text "Hello X from Playwright"`
   - `xbot reply --url "https://x.com/.../status/..." --text "Nice!"`
   - `xbot post-media --text "Hello with image" path/to/image1.jpg path/to/image2.png`
   - `xbot follow https://x.com/<handle>`
   - `xbot unfollow https://x.com/<handle>`
   - `xbot dm https://x.com/<handle> "message text"`
   - `xbot like --url "https://x.com/..."`
   - `xbot retweet --url "https://x.com/..."`

## Blind Spots & Next Steps
- X selectors may drift; `xbot/selectors.py` centralizes them for single-point updates.
- Consider cookie bootstrap (export/import) as primary login to minimize UI flow.
- Add rate limiting and randomized delays to reduce bot-likeness.
- Expand coverage: follow/unfollow, DM, media uploads.

## Violations Check
- No backups; no `/tmp/**`; operations confined to tree-mapped repo.
