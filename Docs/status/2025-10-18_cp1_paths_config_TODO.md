# Critical Path 1: Centralize Paths/Config (xbot.paths + xbot.settings)

## Objectives
- Remove all hardcoded file/dir paths and absolute user paths.
- Provide a single, typed API to resolve repo directories and runtime files.
- Load validated runtime settings from env/.env with safe defaults.

## Deliverables
- New modules: `xbot/paths.py`, `xbot/settings.py`.
- Refactors across scripts to use resolvers.
- Tests: `test_paths.py`, `test_settings.py`.
- Documentation: `Docs/REPO_LAYOUT.md` (outline), migration note in `Docs/status`.

## Design
- `paths.py`: Pure-path resolvers returning `pathlib.Path`; no I/O except helper `ensure_dirs()`.
  - `REPO_ROOT = Path(__file__).resolve().parents[1]`
  - Dirs: `CONFIG_DIR`, `PROFILES_DIR`, `ARTIFACTS_DIR`, `RESULTS_DIR`, `SCREENS_DIR`, `STATE_DIR`, `LOGS_DIR`.
  - Helpers: `dir(name)->Path`, `ensure_dirs(*paths)->None`, `file(kind: str, name: str, create_dirs=True)->Path`.
  - Optional env overrides: `4BOT_REPO_ROOT`, `4BOT_LOGS_DIR`, etc.
- `settings.py`: Pydantic `BaseSettings` + dotenv.
  - Fields: `X_USER: str|None`, `HEADLESS: bool=True`, `RABBITMQ_*`, `VTERM_PORT: int=8765`, `LOG_MAX_BYTES: int=10485760`, `LOG_BACKUPS: int=5`, `PLAYWRIGHT_ENGINE: str = "chromium"`.
  - `get_settings()` returns a cached singleton; `.dict()` dumps effective config.

## Task Breakdown
1) Create `xbot/paths.py`
   - Implement typed constants and functions; docstrings; no comments in code output.
   - Unit: path joining rules; creation guard for `ensure_dirs`.
2) Create `xbot/settings.py`
   - Pydantic model; dotenv load ordering: env > .env > defaults.
   - Export `get_settings()` singleton.
3) Refactor scripts (phase A: minimal surface)
   - `scripts/monitor/monitor_mentions.py`: use `STATE_DIR` and `PROFILES_DIR`; call `ensure_dirs` before writes.
   - `scripts/notification/verify_posts.py`: use `SCREENS_DIR` for screenshots.
   - `scripts/monitor/headless_monitor.py`: use `LOGS_DIR/monitor`; results to `RESULTS_DIR`.
   - `scripts/monitor/generate_health_report.py`: state path via resolver.
4) Refactor scripts (phase B: settings)
   - Replace inline user, ports, headless flags with `get_settings()`.
   - Preserve current behavior; only the source of values changes.
5) Compatibility shims
   - On reads, if canonical file missing, attempt legacy fallback once; warn via logging.
   - On writes, always use canonical path.
6) Tests
   - `tests/test_paths.py`: assert dirs resolve under repo; `ensure_dirs` creates ephemeral subdir in `artifacts/misc` then removes.
   - `tests/test_settings.py`: temp env overrides verified; `.env` fallback works if present.
7) Documentation
   - Create `Docs/REPO_LAYOUT.md` structure; note new canonical paths.
   - Add status entry summarizing migration.

## Acceptance Criteria
- `rg -n "/Users/doctordre"` returns 0 outside `Docs/`.
- `rg -n "replied_mentions.json$"` shows only `artifacts/state` via resolver.
- `pytest -q` passes unchanged; no new skips/failures.
- Running scripts continue to produce outputs under `logs/` and `artifacts/` via resolvers.

## Risks & Mitigations
- Hidden absolute paths in long scripts → ripgrep sweep and focused refactors.
- Env collisions → namespaced `4BOT_*` + sane defaults.
- CI differences → unit tests avoid machine specifics; no `/tmp` usage.

## Timeline (focused)
- Day 0: Implement paths/settings, refactor phase A, tests; run suite.
- Day 1: Refactor phase B, add docs; suite + lint; finalize migration note.

## Metrics
- 0 absolute user paths in code.
- Tests 100% pass.
- Logs and state files present only under `logs/` and `artifacts/`.
