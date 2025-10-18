# Critical Path 9: Robust Config Surface (Typed, Validated, Override-Friendly)

## Objectives
- Establish a single, typed configuration surface that validates inputs and supports layered overrides: defaults → file → env → CLI.
- Replace ad‑hoc JSON/file reads in scripts with a consistent loader that returns Pydantic models.
- Provide developer ergonomics: `xbot config dump|validate|set` commands and clear error messages.

## Deliverables
- New module(s): `xbot/config_model.py` (Pydantic models) and `xbot/config_loader.py` (discovery + precedence + caching).
- Extensions to `xbot/settings` for global toggles and CLI overrides bridging into config.
- CLI additions: `xbot config dump [--json]`, `xbot config validate [--strict]`, `xbot config set <key> <value>` (writes to overlay file with type coercion and validation).
- Sample file: `config/monitor/monitor_config.json` schema-aligned (kept small and commented in docs; code reads JSON only).
- Docs: `Docs/config.md` defining source-of-truth rules, precedence, schema, and examples.

## Design
- Data model in `config_model.py` (Pydantic BaseModel):
  - `MonitorConfig`: browser (engine: literal[chromium, webkit, firefox], headless: bool, scroll_interval: int, scroll_amount: int),
    mention_monitor (interval_minutes: int, max_replies_per_hour: int, reply_chance_general: float, reply_chance_mentions: float),
    logging (level: str, audit_enabled: bool),
    vterm (host: str = "127.0.0.1", port: int = 8765, token: Optional[str]),
    rabbitmq (host: str, port: int, user: str, password: str, vhost: str = "/", exchange: str, request_queue: str, response_queue: str),
    profiles (default: str = "4botbsc").
  - `ConfigBundle`: top-level holding `monitor: MonitorConfig` and possible future sections.
- Loader in `config_loader.py`:
  - Discovery order for base config: `config/monitor/monitor_config.json` then optional overlay `config/profiles/<profile>.json`.
  - Precedence: defaults < base file < overlay file < env vars < CLI overrides.
  - Environment mapping: `XBOT_MONITOR__BROWSER__ENGINE=webkit` style (double underscore to nest), with coercion via Pydantic parsing.
  - CLI overrides accepted as `--config KEY=VALUE` pairs; parsed and applied onto the model prior to validation.
  - Caching: per (profile, env_hash) to avoid repeated disk reads; invalidation hook.
- Error reporting:
  - On validation error, emit a compact, human-readable table: field path | expected | actual | hint.
  - `--strict` mode: unknown keys raise; otherwise ignored with warning.
- Backward compatibility:
  - Existing scripts that read ad-hoc fields (e.g., monitor_config.json) are refactored to call `load_config(profile)` and read from the model.
  - `xbot.settings` remains for global toggles (log max size, level, audit flag) but can read defaults from the model.

## Task Breakdown
1) Implement `xbot/config_model.py`
   - Define `MonitorConfig` and `ConfigBundle` with sensible defaults and validators (bounds for integers, range for percentages, non-empty strings for critical fields).
2) Implement `xbot/config_loader.py`
   - Functions: `load_config(profile: str | None = None, overrides: dict[str, Any] | None = None) -> ConfigBundle`;
     `env_overrides() -> dict`; `apply_overrides(model, overrides)`; `invalidate_cache()`.
   - Env mapping: support `XBOT_` prefix and `__` nesting; coerce bools/ints/floats.
3) CLI integration
   - `xbot.cli`: add group `config` with subcommands `dump`, `validate`, `set`.
   - `dump --json` prints model.json(); otherwise pretty table with key highlights.
   - `validate --strict` returns non-zero on errors; prints table.
   - `set KEY VALUE [--profile <p>]` writes into `config/profiles/<p>.json` overlay; validates before write and refuses if invalid unless `--force`.
4) Script refactors
   - `scripts/monitor/quick_monitor.py`: replace file read of monitor_config.json with `load_config(profile).monitor`.
   - `scripts/monitor/monitor_mentions.py`: adopt `load_config(profile).monitor.mention_monitor` for interval.
   - `scripts/notification/verify_posts.py`: adopt browser engine/headless from config.
   - Defer network creds (RabbitMQ) to env or config if present; no secrets in repo.
5) Tests (see CP5)
   - `test_settings.py` gains env override tests for nested keys.
   - `test_cli_smoke.py` includes `xbot config dump` and `xbot config validate`.
   - New `test_config_loader.py`: env/overlay precedence cases; unknown keys ignored vs strict error.
6) Docs
   - `Docs/config.md`: precedence rules, env mapping syntax (double underscores), examples, and troubleshooting.
   - Update `.env.example` with sample `XBOT_MONITOR__BROWSER__ENGINE` and friends, but commented.

## Acceptance Criteria
- `xbot config dump --json` echoes valid JSON matching schema; `xbot config validate` returns 0 for default repo state.
- Setting env `XBOT_MONITOR__BROWSER__ENGINE=webkit` reflects in dump and affects monitor behavior when run.
- `xbot config set mention_monitor.interval_minutes 10 --profile 4botbsc` writes overlay and validation passes; `dump` shows updated value.
- Scripts no longer open JSON directly for config; they call the loader.
- All tests pass; no regressions.

## Risks & Mitigations
- Env syntax complexity: document clearly; provide examples and CLI `set` to avoid manual errors.
- Secrets handling: encourage env for secrets; redact in dumps unless `--show-secrets` used.
- Performance: caching mitigates repeated reads; models are small.

## Timeline
- Day 0: models + loader + CLI + tests; integrate with one script; suite green.
- Day 1: integrate remaining scripts; docs and examples.

## Metrics
- Zero direct file reads of monitor_config.json in code after refactor.
- Config dump reflects env and overlay changes predictably.
