# Rate Limiting and Playbooks (Oct 16, 2025)

## Summary
- Added rate limiter with jittered global delays between actions.
- Introduced JSON playbooks to run action sequences from the CLI.

## Config
- `RATE_ENABLED=true`
- `RATE_MIN_S=1.0`
- `RATE_MAX_S=3.0`

## CLI
- Run a playbook: `python -m xbot.cli queue run playbooks/sample.json`

## Files
- `xbot/ratelimit.py`: simple min/max interval limiter
- `xbot/playbook.py`: Pydantic schema + runner
- `xbot/cli.py`: `queue run` subcommand
- `playbooks/sample.json`: example

## Tests
- `tests/test_playbook_schema.py` ensures schema loads

## Notes
- Per-step `delay_s` in playbook adds to the global limiter.
- Actions still respect humanize/tracing/HAR settings.

