# Report CLI (Oct 16, 2025)

## Commands
- Summary: `python -m xbot.cli report summary [--index artifacts/results/index.jsonl]`
- CSV Export: `python -m xbot.cli report export-csv [--index artifacts/results/index.jsonl] [--out artifacts/results/index.csv]`

## What it shows
- Total actions, success totals/rates, per-action breakdown, and last failure record (if any).
- CSV includes ts, action, success, meta, artifacts, trace, har columns.

## Notes
- Results are appended automatically per action to `artifacts/results/index.jsonl`.
- Latest action JSON is also written to `artifacts/results/latest.json`.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo.

