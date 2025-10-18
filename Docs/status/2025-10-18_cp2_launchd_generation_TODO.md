# Critical Path 2: Launchd Generation + Install (portable ops)

## Objectives
- Eliminate brittle, hardcoded launchd plists; generate from code using repo/venv aware values.
- Provide idempotent install/uninstall/status flows for macOS launchd jobs.
- Ensure logs and working directories align with new hierarchy.

## Deliverables
- Templates or specs: `bin/launchd/templates/{vterm-http.plist.j2, cz-daemon.plist.j2}` or Python `plistlib` dict specs.
- Generator: `scripts/launch/generate_launchd.py` with subcommands: `render`, `install`, `uninstall`, `status`, `validate`.
- Make targets: `make launchd`, `make launchd-uninstall`, `make launchd-status`.
- Tests: `tests/test_launchd_generator.py` (offline validation via `plistlib` + `plutil -lint` when present).
- Docs: `Docs/launchd.md` and a status entry summarizing migration.

## Design
- Use Python `plistlib` to build dicts → write XML; avoids templating dependency. Optional Jinja2 if human-readable templates are desired.
- Compute venv python: prefer `.venv/bin/python`; fallback to `sys.executable`.
- ProgramArguments: `[python_path, "-m", module, args]`.
- Jobs:
  - `com.4botbsc.vterm-http` → module `xbot.cli` `vterm http --port {settings.VTERM_PORT}`
  - `com.4botbsc.cz-daemon` → module `apps.cz.cz_vterm_rabbitmq_daemon`
- WorkingDirectory: `xbot.paths.REPO_ROOT`
- EnvironmentVariables: minimal (`PATH`, `PYTHONPATH=REPO_ROOT`). Secrets remain in `.env`; app reads via dotenv.
- Logs: `StandardOutPath`/`StandardErrorPath` → `logs/{job}.out.log`, `logs/{job}.err.log`
- KeepAlive: `{ SuccessfulExit: False, Crashed: True }`
- Install path: `~/Library/LaunchAgents/{label}.plist`

## Task Breakdown
1) Spec module: `scripts/launch/generate_launchd.py`
   - CLI (argparse or Typer) with commands: `render [--dry-run]`, `install`, `uninstall`, `status`, `validate`.
   - Build dicts for each job; write to target path; ensure dirs.
   - Detect running job via `launchctl list`; show last log snippet.
   - Validate with `plutil -lint` if available.
2) Integrate paths and settings
   - Use `xbot.paths` for `REPO_ROOT`, `LOGS_DIR`; `xbot.settings` for ports and toggles.
   - Optional: env overrides `4BOT_LAUNCHD_INSTALL_DIR`.
3) Makefile targets
   - `launchd`: `python -m scripts.launch.generate_launchd install`
   - `launchd-uninstall`: `python -m scripts.launch.generate_launchd uninstall`
   - `launchd-status`: `python -m scripts.launch.generate_launchd status`
4) Refactor shell wrappers
   - `scripts/shell/launch_cz_daemon.sh` to call generator `install` when `launchd` arg passed.
   - Remove direct `cp` of static plists.
5) Tests (offline)
   - Build dicts; assert required keys/values; write to temp under `artifacts/misc` and read back via `plistlib`.
   - If `plutil` present, lint file.
6) Documentation
   - `Docs/launchd.md`: prerequisites, usage, troubleshooting, log locations, uninstall steps.
   - Status entry in `Docs/status/` with the change log.

## Acceptance Criteria
- `python -m scripts.launch.generate_launchd render --dry-run` prints valid XML for both labels.
- `make launchd` installs both jobs into `~/Library/LaunchAgents`.
- `make launchd-status` shows jobs present/loaded; `plutil -lint` passes.
- Logs appear under `logs/{vterm_http.*, cz_daemon.*}` when jobs run.
- Shell `launch_cz_daemon.sh` delegates to generator; no direct `cp` of plists remains.

## Risks & Mitigations
- macOS specific tooling (`launchctl`, `plutil`): gate calls; degrade gracefully on non-mac.
- Venv absence: fallback to `sys.executable`; warn.
- Permissions: if install dir not writable, print explicit remediation steps.

## Timeline
- Half day: implement generator + render/install/uninstall/status; integrate Makefile; docs.
- Half day: tests, polish, shell wrapper refactor; validation on target machine.

## Metrics
- Zero manual plist edits; generator is single source of truth.
- Jobs installed and healthy; `status` command green.
- No secrets in plists; logs only under `logs/`.
