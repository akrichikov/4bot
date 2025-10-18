# Next Critical Path TODO (Deterministic, DRY, Zero-Regression)

## 1) Centralize Paths/Config (xbot.paths)
- Goal: Single-source path resolver; eliminate hardcoded/duplicate paths.
- Rationale: Reorg introduced canonical dirs; several scripts still compute paths ad‑hoc.
- Tasks:
  - Add `xbot/paths.py` with: `REPO_ROOT`, `CONFIG_DIR`, `PROFILES_DIR`, `ARTIFACTS_DIR`, `RESULTS_DIR`, `SCREENS_DIR`, `STATE_DIR`, `LOGS_DIR` and helpers (`ensure_dirs()`).
  - Add `xbot/settings.py` to load `.env` via `dotenv`, expose settings (`X_USER`, `RABBITMQ_*`, ports, feature flags).
  - Refactor scripts under `scripts/{monitor,notification,manual,launch}` to import from `xbot.paths` and `xbot.settings` instead of inline `Path(...)`.
  - Replace any `/Users/doctordre/...` and bare literals with resolvers.
- Acceptance:
  - `rg -n "/Users/doctordre|replied_mentions.json|monitor_config.json|profile_verification.png"` returns only references under Docs/.
  - All tests pass; `python -m scripts.monitor.quick_monitor sample 1` works.

## 2) Launchd Generation + Install (portable ops)
- Goal: Generate `.plist` from templates using repo paths/venv automatically.
- Tasks:
  - Implement `scripts/launch/generate_launchd.py` to render `bin/launchd/*.plist.j2` → `~/Library/LaunchAgents/` with correct `WorkingDirectory`, `Standard*Path`, `ProgramArguments` (use `.venv/bin/python`).
  - Add `make launchd` and `make launchd-uninstall` targets.
  - Update Docs to use generator.
- Acceptance:
  - `launchctl load` succeeds; logs under `logs/`.
  - `launchctl list | grep 4botbsc` shows jobs; unload cleans.

## 3) Logging/Rotation & Audit
- Goal: Prevent unbounded log growth; consistent filenames.
- Tasks:
  - Add `xbot/logging_setup.py` with rotating handlers; optional JSONL audit.
  - Integrate in `xbot.cli` and scripts.
  - Optional `scripts/monitor/cleanup_logs.py` (TTL purge).
- Acceptance: rotation at ~10MB x 5, audit preserved; log count stable under load.

## 4) CLI Unification (reduce shell duplication)
- Goal: Typer subcommands for ops; shell wrappers stay minimal.
- Tasks: extend `xbot.cli` with: `ops start|stop|status`, `monitor once|loop`, `verify posts`, `launchd install|uninstall`, `health report`; update shells to delegate.
- Acceptance: `xbot` drives all flows; shells are thin.

## 5) Tests for New Paths
- Goal: Guard against regressions in path layout.
- Tasks: add `test_paths.py`, `test_logging_setup.py`, `test_cli_smoke.py`.
- Acceptance: tests pass in CI; clean collection.

## 6) Requirements/Tooling Consistency
- Goal: Keep `requirements.txt`; pyproject stays authoritative.
- Tasks: document sync policy, add `make dev` to install browsers; add pre‑commit with ruff/black.
- Acceptance: `ruff check .` and `black --check` clean; pre-commit passes.

## 7) Docs Path Sweep
- Goal: Align Docs with new hierarchy; keep legacy appendix.
- Tasks: update path refs; add `Docs/REPO_LAYOUT.md`.
- Acceptance: `rg -n "/Users/doctordre|replied_mentions.json$" Docs/` hits legacy-only.

## 8) Redundancy Consolidation
- Goal: Single storageState location and cookie loader.
- Tasks: canonicalize `config/profiles/4botbsc/storageState.json`; deprecate `auth/4botbsc/...`; unify reads via `xbot.cookies`.
- Acceptance: `rg -n "auth/4botbsc/storageState.json"` returns 0 outside Docs.

## 9) Robust Config Surface
- Goal: Tune via env/CLI with validation.
- Tasks: pydantic model for `monitor_config.json`; env overrides; `xbot config dump`.
- Acceptance: invalid configs produce clear errors; dump prints effective JSON.

## 10) Optional Hardening
- Goal: More resilient runtime.
- Tasks: tenacity retries, per‑step timeouts, headless toggle env; central rate‑limit in `xbot.ratelimit`.
- Acceptance: fewer transient failures; clear backoff in logs.

## Order & Metrics
- Order: 1 → 2 → 3 → 4/5 → 6 → 7 → 8 → 9 → 10
- Metrics: tests 100%; ruff/black clean; no absolute paths in code; launchd jobs healthy; logs rotate; CLI parity.
