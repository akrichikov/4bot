# Critical Path 4: CLI Unification (Operations-first Typer Interface)

## Objectives
- Consolidate operational workflows behind `xbot` Typer CLI; shell scripts become thin wrappers only.
- Provide a stable, discoverable UX for starting services, running monitors, verifying posts, generating health reports, installing launchd jobs, and dumping config.
- Enforce DRY: all path resolution and settings flow through `xbot.paths` and `xbot.settings`.

## Deliverables
- Extended `xbot.cli` with ops-focused subcommands and global options.
- Minimal shell wrappers delegating to `python -m xbot.cli ...` only.
- Smoke tests for CLI commands and help text; docs page with examples.

## Design
- Global options on root app: `--log-level`, `--profile`, `--headless`, `--dry-run`.
- Subcommands (new or consolidated):
  - `ops start`: start vterm HTTP and cz-daemon (foreground), create logs via logging_setup.
  - `ops stop`: stop processes (best-effort), show summary.
  - `ops status`: report port/health/queues, recent log tails from logs/.
  - `monitor once|loop`: wraps scripts.monitor.monitor_mentions (phase A: dispatch via module; phase B: import and run class).
  - `verify posts`: wraps scripts.notification.verify_posts.verify_posts().
  - `launchd install|uninstall|status|render`: delegates to CP2 generator module.
  - `health report`: wraps scripts.monitor.generate_health_report main.
  - `config dump`: prints effective Settings (from xbot.settings) and important path locations (from xbot.paths).

## Task Breakdown
1) CLI scaffolding
   - Add `ops` Typer group with `start|stop|status`.
   - Wire global options at app callback to push values into settings (via context var) and call logging_setup.
2) Command implementations (phase A; reuse existing code)
   - `ops start`: spin up vterm HTTP via asyncio task or subprocess `-m xbot.vterm_http`; start cz-daemon by invoking `xbot.cli cz-daemon` in-process `asyncio.create_task`.
   - `ops stop`: locate processes by known ports/names; best-effort `pkill -f` fallback on Darwin only; print guidance.
   - `ops status`: HTTP check `GET /health` on vterm; show RMQ queues via rabbitmq_manager if available; tail logs/x lines.
   - `monitor` and `verify posts`: import and run their async mains; propagate headless/profile.
   - `launchd *`: `import scripts.launch.generate_launchd as gl; await gl.main(cmd)`.
   - `health report`: call module main to write Docs/status/system_health_audit_final.md; echo path.
   - `config dump`: pretty JSON of settings + key paths.
3) Command implementations (phase B; polish)
   - Add `--json` output for status.
   - Add `--timeout` to `monitor once`; `--interval` for loop.
   - Pass `--audit` to enable audit JSONL.
4) Tests
   - `tests/test_cli_smoke.py`: invoke `xbot --help`, `xbot ops --help`, `xbot config dump --json` via subprocess; assert exit codes and key strings.
   - `tests/test_cli_paths.py`: ensure `config dump` prints canonical dirs.
   - `tests/test_cli_status_parse.py`: with vterm server mocked (or skip), ensure graceful degradation and JSON skeleton.
5) Shell wrappers (phase-down)
   - Update scripts/shell/*.sh to call CLI (already mostly delegated); keep user-facing messages and colors; no business logic.
6) Docs
   - `Docs/cli.md`: quickstart, examples for each command, environment overrides, troubleshooting.
   - Status entry noting convergence under CLI.

## Acceptance Criteria
- `xbot ops start` launches both vterm HTTP and cz-daemon; logs under `logs/`; `xbot ops status` shows healthy when service running.
- `xbot monitor once` runs without exceptions and respects `--profile` and `--headless`.
- `xbot config dump` prints effective values from `.env` overrides and defaults.
- Shells merely delegate; no more direct path handling or `cp` of plists.
- Tests pass; help text lists all commands with one‑line descriptions.

## Risks & Mitigations
- Process supervision complexity: prefer `launchd` for long‑running; CLI ops intended for dev/local use.
- Mixed async/subprocess: keep per‑command timeouts and clear error messages.

## Timeline
- Day 0: add ops group + config dump + launchd delegation + monitor/verify wrappers + tests.
- Day 1: status JSON, polish help/docs, shell delegation cleanup.

## Metrics
- Shell LOC reduced; CLI commands cover 100% of common workflows.
- Help coverage complete; smoke tests green.
