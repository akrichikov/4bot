# 2025-10-18 Status Index + Health CLI – Implementation

## Summary
- Implemented a minimal status index generator and wired it into the CLI and Makefile.
- Added guard tests remain green.

## Commands
- JSON only: `xbot health system --json-out Docs/status/system_health.json`
- HTML+JSON: `xbot health system-html --out-html Docs/status/system_health.html --out-json Docs/status/system_health.json`
- Index: `xbot health status-index` (writes `Docs/status/index.html`)
- Make targets: `make system-health-html` and `make status-index`

## Code Changes
- `xbot/report_health.py`
  - `write_status_index(outdir: Path) -> Path`: builds a simple `index.html` linking to `system_health.html/.json` if present.
- `xbot/cli.py`
  - Added `health status-index` subcommand.
  - (Existing) `health system` and `health system-html` used by Makefile now exercised.
- `Makefile`
  - Added `status-index` target.
- Tests
  - `tests/test_status_index.py`: validates `write_status_index` generates links when artifacts exist.

## Validation
- `pytest -q` → green (1 skip, rest pass)
- `make system-health-html` → writes HTML+JSON under `Docs/status/`
- `make status-index` → writes `Docs/status/index.html`

## Notes
- The index generator is intentionally minimal and static to avoid any runtime dependencies.
- CI `ci.yml` already uploads `Docs/status` as `xbot-reports`, so the index will be included.
