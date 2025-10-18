# Critical Path 5: Test Suite Expansion (Paths, Logging, CLI, Launchd)

## Objectives
- Add targeted tests to lock in the new repo layout, path resolvers, logging rotation/audit behavior, CLI surface, and (offline) launchd spec generation.
- Ensure fast, reliable tests that run without external services by default; mark live/system tests clearly.

## Deliverables
- New tests under `tests/`: `test_paths.py`, `test_settings.py`, `test_logging_setup.py`, `test_cli_smoke.py`, `test_cli_status_json.py`, `test_launchd_generator.py`, `test_repo_contracts.py`.
- Fixtures in `tests/fixtures` and `conftest.py` updates for temp dirs/env overrides.
- Markers: `@pytest.mark.offline`, `@pytest.mark.system`, `@pytest.mark.live` where appropriate.

## Test Design
- Offline-first: no network/process unless explicitly marked; filesystem isolated via `tmp_path` monkeypatching `xbot.paths` overrides.
- Deterministic: seed randomness where used; assert shapes/keys and critical values only.
- Granular: each module gets a focused test; broader smoke tests for CLI and contracts.

## Test Specs
1) `test_paths.py`
   - Arrange: monkeypatch `4BOT_REPO_ROOT` to repo root; import `xbot.paths`.
   - Assert: all dir constants exist and are under repo; `paths.ensure_dirs` creates nested dir under `artifacts/misc` and is idempotent.
   - Assert: `file(kind,name)` joins correctly and creates parent dirs when requested.
2) `test_settings.py`
   - Arrange: with tmp `.env` via monkeypatch env; override `X_USER`, `LOG_LEVEL`; call `get_settings()`.
   - Assert: values reflect env and defaults; types are correct.
3) `test_logging_setup.py`
   - Arrange: `init_logging` to logs under tmpdir via paths override; `LOG_MAX_BYTES` small (e.g., 2KB).
   - Act: write >2KB of log lines; emit `audit_event` with payload.
   - Assert: rotation produced `.1` file; JSONL line parses; contains `event`, `payload`, `run_id` keys.
4) `test_cli_smoke.py`
   - Invoke `xbot --help` and `xbot config dump` via subprocess with `PYTHONPATH` set to repo; assert exit code 0, expected substrings present.
5) `test_cli_status_json.py`
   - Invoke `xbot ops status --json` expecting graceful output with required keys (healthy flags false when not running); no exceptions.
6) `test_launchd_generator.py` (offline)
   - Import generator build fn; get dict for vterm-http and cz-daemon; assert required keys/values; write to tmp; if `plutil` available, lint.
7) `test_repo_contracts.py`
   - Scan codebase: no absolute `"/Users/doctordre"` strings outside `Docs`; no `logging.basicConfig` outside `xbot/logging_setup.py`; all shell scripts live in `scripts/shell`.

## Fixtures & Utilities
- `env_guard` fixture: clears and restores env keys for settings.
- `path_override` fixture: monkeypatch `xbot.paths` directories to tmp base when needed.
- `plist_lint_available` helper: detects `plutil` presence to conditionally run lint.

## Acceptance Criteria
- `pytest -q` passes locally; collection shows new tests; offline by default.
- Ripgrep scans in contracts test pass (0 violations) after CP1–CP4 integrations.
- Rotation and audit tests are deterministic and fast (<1s each).

## Risks & Mitigations
- Flakiness due to subprocess CLI: keep timeouts and capture output; avoid parallelism for those tests.
- Platform-specific `plutil`: skip lint on non-macOS.

## Timeline
- Add tests and fixtures Day 0; run suite and adjust; stabilize within the day.

## Metrics
- New tests increase suite count and cover: paths (100%), settings (100%), logging (core), CLI (smoke), launchd (spec), code hygiene (contracts).
