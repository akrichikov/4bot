# Scheduler and Samples (Oct 16, 2025)

## Schedule Runner
- Command: `python -m xbot.cli schedule run schedules/sample.json`.
- Options:
  - `--dry-run` prints the next due run and exits.
  - `--once` runs the next due run then exits.

## Spec Format (JSON)
- `tasks[].playbook` path
- `tasks[].times`: list of HH:MM 24h local times
- `tasks[].days`: optional list of `mon..sun`
- `tasks[].jitter_s`: optional seconds to offset start time
- `tasks[].enabled`: default true

## Samples
- `playbooks/sample.json` – example playbook
- `schedules/sample.json` – sample schedule

## Notes
- Uses local time; no background daemon – call from a process manager if needed.
- Global rate limiter still applies.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo.

