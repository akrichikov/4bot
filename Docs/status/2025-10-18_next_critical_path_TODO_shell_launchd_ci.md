Next Critical Path TODO — Shell, Launchd, CI Hardening
Date: 2025-10-18

1) Launchd templating & install helper
- Add `scripts/launch/install_launchd_from_templates.py` to render `Docs/launchd/*.template.plist` using env or CLI flags.
- Acceptance: `launchctl load` succeeds; rendered plists contain no absolute `/Users/` literals.

2) Module-mode everywhere for launchers
- Ensure all shell invocations use `python -m ...` or absolute repo paths. Remove any lingering file-relative runs.
- Acceptance: `rg -n "python .*\.py\b" scripts` returns zero, excluding scripts in `scripts/manual/`.

3) Secrets abstraction skeleton
- Add `xbot/secrets.py` interface with `get(name)`, `set(name, value)`, `delete(name)` and a no-op file backend behind a feature flag.
- Acceptance: unit tests for `redact()` and secrets stub pass; no plaintext prints of sensitive keys.

4) Profiles & paths doc sweep
- Expand `Docs/architecture/paths_and_profiles.md` with env overrides, examples, and CLI usage (`xbot profile info/doctor/set-default`).
- Acceptance: doc examples run locally without edits; paths resolve via helpers.

5) CI guardrails
- Add grep gates for `/Users/` in code (exclude Docs/templates) and for secret-like tokens in logs.
- Acceptance: CI fails on violations; local `make hygiene` remains green.

6) Wrapper dedup audit
- Verify all `scripts/*` wrappers delegate to canonical modules under `xbot/` or `apps/`.
- Acceptance: `tests/test_wrapper_hygiene.py` updated to assert import delegation for new wrappers.

7) CLI unit tests
- Add basic tests for `xbot.cli profile info/doctor` and `health system-html` smoke.
- Acceptance: `pytest -q` green.

8) Launchd docs
- Extend `Docs/launchd/README.md` with common troubleshooting and `launchctl` commands.
- Acceptance: Try-out steps succeed on a clean machine.
