# 2025-10-18 Pre-commit Hooks Setup

- Added `.pre-commit-config.yaml` with hooks: end-of-file-fixer, trailing-whitespace, check-added-large-files, ruff (with --fix), black.
- Make targets:
  - `pre-commit-install` – installs pre-commit in venv and sets up git hooks.
  - `pre-commit-run` – runs hooks across the repo.
- CI now executes `pre-commit run --all-files` in the lint job.

Usage:
- `make pre-commit-install` once per clone.
- `make pre-commit-run` to run hooks locally.

Notes:
- Hooks operate only within the repo; no /tmp usage.
- Ruff/Black config comes from `pyproject.toml`.
