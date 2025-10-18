# Critical Path 3: Logging, Rotation, and Structured Audit

## Objectives
- Unify logging across the codebase with a single, configurable setup.
- Enforce rotating file logs in `logs/` and structured JSON audit logs for machine consumption.
- Remove ad‑hoc `logging.basicConfig` and `print()` usage in scripts; preserve behavior and verbosity controls.

## Deliverables
- New module: `xbot/logging_setup.py` (`init_logging`, `get_logger`, `audit_event`, adapters).
- Settings integration: `LOG_MAX_BYTES`, `LOG_BACKUPS`, `LOG_LEVEL`, `AUDIT_ENABLED`, `AUDIT_FILE`.
- Script/CLI integration: `xbot.cli` initializes logging; scripts use `get_logger()`.
- Tests: `test_logging_setup.py` (rotation, JSON audit shape, adapter context); `test_print_migration.py` (smoke: no basicConfig leaks).
- Docs: `Docs/logging.md` and status entry summarizing migration.

## Design
- Initialization: `init_logging(settings, paths, service_name:str)` builds two handlers:
  - `RotatingFileHandler` at `logs/{service_name}.log` (size `LOG_MAX_BYTES`, backup `LOG_BACKUPS`).
  - `StreamHandler` to stdout with concise human format.
- JSON audit: dedicated logger name `"xbot.audit"` writing JSONL to `logs/audit/{service_name}.jsonl` when `AUDIT_ENABLED`.
- Formatters:
  - Human: `"%(asctime)s | %(levelname)s | %(name)s | %(message)s"` (ISO8601 time, 24h).
  - JSON: dict with keys `{timestamp, level, logger, module, func, line, message, event, payload, run_id, correlation_id}` serialized via `json.dumps`.
- Context propagation:
  - Use `contextvars` for `run_id` and `correlation_id`; helper `set_log_context(run_id:str=None, correlation_id:str=None)`.
  - `get_logger(name)` returns `LoggerAdapter` injecting context keys.
- Convenience:
  - `audit_event(event:str, payload:dict)` writes one JSONL line with context + payload.
  - `ensure_dirs` for `logs/` and `logs/audit/` via `xbot.paths`.
- Levels & control:
  - Default level `INFO`; override via env/CLI flag `--log-level`.
  - Silence noisy third‑party logs (playwright, aiohttp) to `WARNING` by default.

## Task Breakdown
1) Implement `xbot/logging_setup.py`
   - `init_logging`, `get_logger`, `set_log_context`, `audit_event`; helper `_json_dumps`.
   - Respect settings for sizes/backups/levels; derive `service_name` default from `__name__` or CLI arg.
2) Settings wiring
   - Extend `xbot.settings` with fields: `LOG_LEVEL` (str, default `"INFO"`), `LOG_MAX_BYTES` (int = 10485760), `LOG_BACKUPS` (int = 5), `AUDIT_ENABLED` (bool = True), `AUDIT_FILE` (Optional[str]).
3) CLI integration
   - In `xbot.cli`: at app startup invoke `init_logging(settings, paths, service_name="xbot")`; add `--log-level` option mapping to settings override.
   - Ensure subcommands (vterm http, health, notify parser) inherit configured root logger.
4) Script integration (phase A)
   - `scripts/monitor/monitor_mentions.py`: replace `print` with `logger.info/debug`; `service_name="monitor"`.
   - `scripts/notification/verify_posts.py`: use logger; keep terminal prompts via `logger.info`.
   - `scripts/monitor/headless_monitor.py`: remove `logging.basicConfig`; call `init_logging` with `service_name="headless_monitor"`; route AI alerts via `audit_event("ai_post", payload)`.
   - `scripts/manual/manual_event_monitor.py`: remove `basicConfig`; rely on central init.
5) Script integration (phase B)
   - Shells remain; Python modules they invoke will initialize logging.
6) Tests
   - `tests/test_logging_setup.py`: initialize logging to `artifacts/misc/test_logs`; write > `LOG_MAX_BYTES` to trigger rotation; assert `.1` exists; parse JSONL audit and validate keys; verify `LoggerAdapter` injects `run_id`.
   - `tests/test_print_migration.py`: scan repo for stray `logging.basicConfig(` outside logging_setup; smoke run of `get_logger`.
7) Docs
   - `Docs/logging.md`: formats, levels, file locations, rotation policy, audit schema, set run_id/correlation_id.
   - Status update with tail examples.

## Acceptance Criteria
- `python -m xbot.cli --log-level DEBUG` creates `logs/xbot.log` with rotation and emits structured audit lines when enabled.
- `scripts/monitor/headless_monitor.py` writes to `logs/headless_monitor.log` and audit events to `logs/audit/headless_monitor.jsonl`.
- `rg -n "logging.basicConfig\("` returns only in `xbot/logging_setup.py`; zero in scripts.
- All tests pass; no regressions in pytest suite.

## Risks & Mitigations
- Double handlers: `init_logging` idempotent guard.
- Multi‑process rotation: stdlib rotation is process‑unsafe; document and recommend per‑service separation.
- Performance: JSON dumps overhead; keep audit minimal and optional.

## Timeline
- Day 0: module + CLI + two scripts + tests; suite green.
- Day 1: remaining script integrations, docs, polish.

## Metrics
- Unified log format across targeted scripts.
- Rotations observed at configured size; max backup count enforced.
- Audit JSONL schema stable and validated in tests.
