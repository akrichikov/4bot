# Repo Scan and Test Status (2025-10-16)

## Commands Executed
- `pwd`
- `ls -la`
- `tree -a` (fallback to `find` if unavailable)
- `. .venv/bin/activate` and dependency install (playwright, pytest, etc.)
- `pytest --collect-only`
- `pytest tests`

## Key Outputs (abridged)
- CWD: `/Users/doctordre/projects/4bot`
- Collect-only discovered:
  - `browser_cookie_test.py: 1`
  - `tests/test_collect_only.py: 1`
  - `tests/test_health_imports.py: 1`
  - `tests/test_playbook_schema.py: 1`
  - `tests/test_profiles.py: 1`
  - `tests/test_state_json_shape.py: 1`
- Test run (tests/): `s.... [100%]`

## Identified Paths
- Package: `xbot/` (modules: `cli.py`, `browser.py`, `profiles.py`, `playbook.py`, etc.)
- Tests (automated): `tests/` (5 tests + 1 live-skipped)
- Test-like interactive scripts (manual):
  - `browser_cookie_test.py` (infinite interactive session)
  - `test_event_monitor.py` (Playwright headful monitor)
  - `test_monitor_safe.py` (Playwright headful monitor)
  - `test_decryption.py` (Chrome cookie decryption utility)
- Docs: `Docs/` and `Docs/status/`

## Environment Notes
- Python: `3.14.0`
- Venv: `.venv` (used for installs and pytest)
- Dependencies from pyproject resolved; Playwright browsers not installed (not needed for import-only tests).

## Violations Check
- Backups created: 0
- `/tmp` usage: 0
- Duplicates introduced: 0
- All operations confined to tree-mapped paths: Yes

## Risks & Blind Spots
- Running full `pytest` without path filter would execute `browser_cookie_test.py::test_browser_cookies` and hang (infinite loop for manual inspection).
- `test_event_monitor.py` and `test_monitor_safe.py` require live browser and cookies; unsuitable for CI.
- `test_decryption.py` imports `Crypto.*` (pycryptodome) not declared in pyproject; executing it in pytest context could fail or perform system reads.

## Clarification Required
- Should interactive scripts at repo root be:
  1) Marked with `@pytest.mark.live` to skip by default, or
  2) Excluded from pytest discovery via `testpaths = ["tests"]` in pyproject, or
  3) Renamed to avoid pytest patterns (e.g., `*_script.py`)?
- Preferred default: keep automated suite under `tests/`; mark interactive scripts as `live`.

## Next Proposed Steps
- Add `@pytest.mark.live` to `browser_cookie_test.py::test_browser_cookies`.
- Optionally set `[tool.pytest.ini_options] testpaths = ["tests"]` to constrain CI scope.
- If desired, provide a separate "integration" tox/Make target invoking interactive scripts manually.
