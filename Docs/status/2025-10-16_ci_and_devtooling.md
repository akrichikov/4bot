# CI and Dev Tooling (Oct 16, 2025)

## CI
- Workflow: `.github/workflows/ci.yml`
  - Python 3.12; installs project + dev deps
  - Installs Playwright Chromium
  - Runs `ruff check` and `pytest -q`

## Dev
- `pyproject.toml` optional deps `dev`: ruff, black
- `Makefile` targets: `venv`, `install`, `dev`, `lint`, `format`, `test`, `health`
- `bin/dev-setup.sh` initializes venv, installs deps, installs browser

## Ruff/Black
- `tool.ruff` and `tool.black` configured in `pyproject.toml`

## Violations Check
- No backups; no `/tmp/**`; changes remain within repo tree.

