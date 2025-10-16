# HTML Report (Oct 16, 2025)

## Command
- `python -m xbot.cli report html --index artifacts/results/index.jsonl --out artifacts/results/report.html --actions post,reply --limit 200`

## Details
- Reads `index.jsonl`, filters optionally by actions, limits to N records.
- Produces a self-contained HTML summary with action outcome, meta, and artifact paths.

## Notes
- Traces/HAR/artifacts paths are printed for quick navigation; files are not embedded.

## Violations Check
- No backups; no `/tmp/**`; confined to repo tree.

