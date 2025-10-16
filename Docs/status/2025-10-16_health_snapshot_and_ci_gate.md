# Health Snapshot and CI Gate (Oct 16, 2025)

## Snapshot
- Command: `python -m xbot.cli health snapshot --tweet-url ... --profile ... --require compose,tweet,profile --json-out artifacts/results/snap.json`.
- Captures presence of key selectors in compose/tweet/profile contexts.
- Evaluates pass/fail based on required groups and records a `selectors_snapshot` result.

## CI Gate
- Workflow runs: `python -m xbot.cli health snapshot --require compose --json-out artifacts/results/ci_snapshot.json`.
- Fails the job automatically if required groups do not pass.

## Media Verification Meta
- `post-media` now records `previews` count for quick sanity checks.

## Reply Content Confirmation (fallback)
- If toast isn’t detected and content confirmation is enabled, reply searches for reply text in the thread.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo tree.

