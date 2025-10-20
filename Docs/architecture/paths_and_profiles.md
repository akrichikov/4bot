Paths & Profiles — Unified Model
================================

Goals
- Single source of truth for all important directories.
- No user-specific absolute paths; repo-relative or env-driven only.
- Profile-aware resolution for storageState and user-data.

Key APIs
- `xbot.profiles.storage_state_path(profile)` — preferred storageState.json
- `xbot.profiles.user_data_dir(profile)` — Playwright persistent dir
- `xbot.profiles.cookie_candidates(profile)` — discovery order for cookies
- `xbot.profiles.validate(profile)` — quick PASS/FAIL with hints

Environment Overrides
- `ARTIFACTS_DIR` (default: `artifacts/`)
- `LOGS_DIR` (default: `logs/`)
- `NOTIFICATION_LOG_DIR` (default: `notification_json_logs/`)
- `PROFILE` (default: `default`)

CLI Quickstart
```bash
# Inspect profile paths
python -m xbot.cli profile info default

# Doctor check
python -m xbot.cli profile doctor 4botbsc

# Set default profile (non-destructive; writes config/active_profile)
python -m xbot.cli profile set-default 4botbsc

# Show resolved paths (roots + profile paths)
python -m xbot.cli paths show

# Doctor paths (exists/writable; optional ensure)
python -m xbot.cli paths doctor --ensure

# Health JSON/HTML + index
make system-health-html && make status-index
```

Storage & Cookies
- Preferred on-disk location: `config/profiles/<name>/storageState.json`
- Legacy fallbacks supported: `auth/<name>/storageState.json`, `auth/storageState.json`
- Cookie discovery includes `auth_data/x_cookies.json` and Chrome export defaults.
Profile Precedence
- PROFILE or X_PROFILE environment variable (highest)
- config/active_profile file (if present)
- default

Writing Artifacts/Logs
- All logs under `cfg.logs_dir`; all outputs under `cfg.artifacts_dir`.
- Avoid direct `open()` to arbitrary paths in application code.

Makefile Shortcuts
- `make paths-show` → prints the resolved directories.
- `make paths-json` → writes JSON to `Docs/status/paths.json` (also included in `make site` and `make site-all`).
- `make paths-doctor` → validates/ensures configured roots and writes `Docs/status/paths_doctor.json` (also included in `make site`).
- `make site-clean` → removes generated `Docs/status/*.html` and `Docs/status/*.json` (safe cleanup).
- `make site-reset` → clean + rebuild full status site pipeline.
- `make paths-export` → writes all path artifacts (`paths.json`, `paths_env.json`, `paths_doctor.json`, `paths.md`). Used by `make site` and `make site-all`.
- `make site-cli` → builds the entire status site via the Python CLI (`xbot.cli site build`). Use `STRICT=true` and/or `HEALTH=true` to enable validation and health generation.
