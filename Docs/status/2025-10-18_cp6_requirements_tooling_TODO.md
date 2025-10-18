# Critical Path 6: Requirements, Tooling, and Developer Workflow Consistency

## Objectives
- Make dependency management predictable while honoring the repo’s requirement to keep `requirements.txt` unpinned.
- Provide a frictionless developer workflow (bootstrap, lint, format, test, run browsers) reproducible on macOS.
- Add pre-commit hygiene, conventional Make targets, and CI entry-points (local-first; CI can reuse).

## Deliverables
- `requirements.txt` as the end-user installation surface (unpinned), synchronized with `pyproject` groups.
- Makefile targets: `init`, `dev`, `install`, `lint`, `fmt`, `type` (optional), `test`, `clean`, `playwright`, `sync-reqs`, `hooks`.
- Pre-commit configuration with ruff/black and basic hygiene hooks.
- Updated `.env.example` covering new settings (e.g., `LOG_LEVEL`, `AUDIT_ENABLED`, `LOG_MAX_BYTES`, `LOG_BACKUPS`, `VTERM_PORT`).
- Optional: docs page for setup + troubleshooting.

## Design
- Source of truth: `pyproject` for metadata; `requirements.txt` for pip installs (unpinned). Keep both aligned with a tiny sync script.
- Sync strategy (no pinning):
  - `scripts/orchestrator/sync_requirements.py` reads `pyproject.toml` `[project.dependencies]` and `[project.optional-dependencies].dev` and writes `requirements.txt` with top-level packages only (no versions), each on a separate line, stable-sorted, deduped.
  - Dev installs via `pip install -e .[dev]` remain supported; `requirements.txt` remains for users preferring `pip install -r requirements.txt`.
- Tooling:
  - `ruff` and `black` already configured in `pyproject`; expose via Make.
  - Pre-commit hooks: trailing-whitespace, end-of-file-fixer, mixed-line-ending, check-added-large-files, black, ruff.
  - Optional typing: `mypy` or `pyright`; stage behind a Make target.
- Playwright:
  - Ensure `make dev` runs `python -m playwright install chromium`.
- Git ignore:
  - Confirm `logs/` and `artifacts/` excluded; `logs/audit/` covered via `logs/`.

## Task Breakdown
1) Requirements sync script
   - Create `scripts/orchestrator/sync_requirements.py` that:
     - Loads `pyproject.toml`, reads deps and dev extras.
     - Normalizes names (strip extras and version constraints, keep base package name when safe).
     - Writes `requirements.txt` with a header comment noting auto-generation policy, unpinned by design, grouped as core + dev comments.
   - Add `make sync-reqs` to run it.
2) Makefile upgrades
   - `init`: create venv and upgrade pip; `dev` installs editable + dev extras + playwright.
   - `lint`: `ruff check .`; `fmt`: `black xbot apps scripts tests` then optional `ruff check --fix`.
   - `type` (optional): mypy/pyright placeholder.
   - `clean`: remove caches and build artifacts.
3) Pre-commit
   - Add `.pre-commit-config.yaml` with hooks as above.
   - Add `make hooks` to install pre-commit and `pre-commit install`.
4) `.env.example` updates
   - Add new keys: `LOG_LEVEL`, `AUDIT_ENABLED`, `LOG_MAX_BYTES`, `LOG_BACKUPS`, `VTERM_PORT` with concise comments.
5) Documentation
   - `Docs/dev_setup.md`: bootstrap steps, make targets, Playwright install, troubleshooting.
   - Status note explaining policy: `requirements.txt` remains unpinned by design.

## Acceptance Criteria
- `make init && make dev` sets up venv, installs project + dev extras, installs Playwright Chromium, exits cleanly.
- `make lint` and `make fmt` run clean on committed tree; fail with actionable messages when issues exist.
- `pre-commit run --all-files` passes after formatting/linting.
- `make sync-reqs` regenerates `requirements.txt` deterministically and without pins; content reflects pyproject core+dev packages.
- `.env.example` includes all new configurable fields introduced by CP3.

## Risks & Mitigations
- Divergence between `requirements.txt` and `pyproject`: addressed by sync script and `make sync-reqs`; documented.
- Pre-commit friction on large files: set sensible large-file threshold and exclude `artifacts/`.
- Python version drift: rely on system Python; optional pyenv/asdf note in docs, not required.

## Timeline
- Half day: sync script + Make targets + pre-commit + `.env.example`; quick doc.
- Half day: iterate from lint feedback and real run.

## Metrics
- Fresh clone to first test run reduced to a single `make dev`.
- `requirements.txt` regenerates without manual edits; diffs are minimal and sorted.
