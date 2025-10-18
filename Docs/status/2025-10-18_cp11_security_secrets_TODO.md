# Critical Path 11: Security, Secrets, and Credentials Hygiene

## Objectives
- Eliminate accidental secret leakage and centralize credential handling with encryption-at-rest and least-privilege defaults.
- Provide a consistent developer workflow for loading, rotating, auditing, and redacting secrets across local/dev automation and launchd services.
- Add automated guardrails (scanners + hooks) without obstructing normal development.

## Deliverables
- Secrets module: `xbot/secrets.py` (`load_secret`, `set_secret`, `delete_secret`, `list_secrets`) with pluggable backends (env, Keychain/macOS, file+AES-GCM).
- Encrypted secrets store: `artifacts/state/secrets.json.enc` (AES‑GCM via pycryptodome; key bound to macOS Keychain item or passphrase via PBKDF2).
- Redaction utilities: `redact(value)` + logging filter wired into logging_setup to prevent secret printing.
- Pre-commit scanner integration (optional): simple regex checks + allowlist; gitleaks/trufflehog optional doc guidance.
- CLI: `xbot secrets get|set|list|rm|rotate`.
- Docs: `Docs/security.md` and updated `.env.example` (placeholders only; no default secrets).

## Design
- Backends (priority order):
  1) Env: `os.environ[NAME]` for runtime injection in launchd; never persisted.
  2) Keychain (macOS): store/retrieve by `service="4bot"`, `account=NAME` using `security` CLI; fallback if unavailable.
  3) File+AES-GCM: `secrets.json.enc` under `artifacts/state`; 32-byte key from passphrase (prompt or env `4BOT_SECRETS_KEY`) via PBKDF2-HMAC-SHA256 (200k iters) + random salt; per-record random nonce; versioned envelope `{kdf:{salt,iters}, entries:{NAME:{n,ct,tag}}}`.
- `xbot/secrets.py` chooses backend by availability + explicit env (`4BOT_SECRETS_BACKEND=keychain|file|env`).
- Redaction: logging filter that replaces any detected secret values in log messages with `***`; keep a small rolling set of secret values for masking.
- Rotation: `set_secret` replaces old record and returns rotated timestamp; CLI prints safe summary.
- Launchd: plists never store secrets; rely on env (`launchctl setenv`) or Keychain backend at runtime.

## Task Breakdown
1) Secrets backend + crypto
   - Implement Keychain wrapper (subprocess `security add/find/delete-generic-password`); handle updates.
   - Implement File+AES‑GCM store: load/save, passphrase prompt helper, headless mode via `4BOT_SECRETS_KEY`; unit tests for round‑trip.
   - Implement Env backend (read‑only by default); `set_secret` warns/refuses unless `4BOT_ALLOW_ENV_WRITE=true`.
2) API surface and CLI
   - `xbot/secrets.py`: `load_secret`, `set_secret`, `delete_secret`, `list_secrets`; redact util and logging filter.
   - `xbot.cli` secrets group: `get/set/list/rm/rotate`; `--backend`, `--passphrase` (prompted), `--show` to print.
3) Integration
   - Replace ad‑hoc reads: RabbitMQ creds, vterm token, X creds use secrets API; scripts read via secrets loader or env.
   - `logging_setup` adds redact filter initialized with known secrets (best effort).
4) Guardrails
   - Pre-commit: add simple regex checks for common tokens and deny adding secrets in tracked files; allowlist artifacts/ and Docs/status if needed.
   - Optional doc guidance for gitleaks/trufflehog.
5) Docs + `.env.example`
   - `Docs/security.md`: storage options, Keychain vs file+AES, rotation, launchd env usage.
   - `.env.example`: include names only (e.g., `RABBITMQ_PASSWORD` resolved by secrets backend or env at runtime).

## Acceptance Criteria
- Secrets set/retrieved with Keychain on macOS; fallback to file+AES works with `4BOT_SECRETS_KEY`.
- No secrets written to plists, logs, or committed files; redaction filter masks known values.
- `xbot secrets list` shows names and timestamps only unless `--show` used.
- Unit tests pass for round‑trip encryption, KDF, Keychain wrapper (mocked).

## Risks & Mitigations
- Keychain availability: fallback to file+AES with strong KDF; document passphrase management.
- Developer friction: clear CLI + docs; optional caching of passphrase.
- False positives in scanners: allowlist + targeted patterns only.

## Timeline
- Day 0: backends + CLI + tests; docs skeleton.
- Day 1: integrate with RMQ/vterm token reads; add redaction filter; finalize docs.

## Metrics
- Zero secrets detected by scanners; redaction observed in logs.
- Time to set a new secret < 1 minute.
