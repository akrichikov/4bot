# Critical Path 8: Redundancy Consolidation (Profiles, Cookies, State, Scripts)

## Objectives
- Canonicalize profile storage state and cookie handling to a single source of truth.
- Remove functional duplication by routing all reads/writes through central APIs while preserving backward compatibility (no feature loss).
- Normalize runtime state file locations (e.g., `replied_mentions.json`) and deprecate scattered paths.

## Deliverables
- Updated profile path resolution API in `xbot.profiles` (canonical path + compatibility fallback).
- Cookies API hardened in `xbot.cookies` (best‑effort loader already present; add canonical writer and schema guards).
- Migrations in scripts to use canonical resolvers; optional symlink helper for legacy dirs.
- Repo sweep and contracts test to catch regressions.

## Design
- Canonical profile storage state: `config/profiles/<profile>/storageState.json`.
- Legacy read fallback: `auth/<profile>/storageState.json` and `auth/storageState.json` for default.
- Writer policy: all writes go to canonical; do not write to legacy paths.
- Cookie handling:
  - Keep `load_cookies_best_effort(profile)` as the universal reader (already merges multiple sources + x.com variants).
  - Add `write_storage_state(storage: dict, profile)` in `xbot.cookies` that writes only to canonical and ensures parent dirs.
  - Add strict validator for cookie dict shape when merging; drop/repair invalid entries.
- Profiles API changes in `xbot.profiles`:
  - New: `canonical_profile_paths(profile)` returns `(storage_state_path, user_data_dir)` using `config/profiles` + `.x-user/<profile>`.
  - Deprecate/redirect `profile_paths()` to call `canonical_profile_paths()`; maintain signature but return canonical; add legacy detection util `legacy_profile_paths(profile)` for sweeps and doc-lint.
  - Update `ensure_profile_dirs`, `clear_state` to act on canonical; add `clear_legacy_state(profile)` helper.
- Runtime state files:
  - Already consolidated: `artifacts/state/replied_mentions.json`. Add guard helpers in `xbot.paths` soon to obtain this path across scripts.
- Sweeps:
  - ripgrep scan for `auth/<profile>/storageState.json` and root `auth/storageState.json` references in code/scripts; refactor to APIs.
  - ripgrep scan for raw `replied_mentions.json` usage (already updated most; verify).
- Compatibility strategy:
  - Keep reading from legacy state when canonical missing (read‑only); offer a one‑time migration command under `xbot.cli profile migrate --profile <name>` to copy/move legacy → canonical (interactive or `--force`).

## Task Breakdown
1) `xbot.profiles` refactor
   - Implement `canonical_profile_paths`, `legacy_profile_paths`.
   - Update `profile_paths` to return canonical; keep name for backward compatibility.
   - Update `ensure_profile_dirs`, `clear_state` to target canonical; add `clear_legacy_state`.
2) `xbot.cookies` enhancements
   - Implement `write_storage_state(path: Path, storage: dict)` and `write_storage_state_for_profile(profile, storage)` → canonical.
   - Add `validate_cookie(c)`; harden merge in `merge_into_storage` to drop invalid keys and normalize domain/path.
   - Keep `load_cookies_best_effort` behavior; ensure dedupe across twitter.com/x.com remains.
3) Script migrations
   - Replace direct `Path("auth/.../storageState.json")` and manual writes with `canonical_profile_paths` and `write_storage_state_for_profile`.
   - Confirm updated scripts from CP1 are aligned; sweep remaining references in `scripts/*` and `apps/*`.
4) Optional symlink helper (non‑default)
   - CLI: `xbot profile migrate --profile <name> [--move|--copy]` to move/copy legacy state to canonical and optionally symlink legacy path → canonical for external tools.
5) Repo contracts test updates (see CP5)
   - Extend contracts test to assert no code references `auth/<profile>/storageState.json` outside tests/docs.
6) Documentation
   - Update REPO_LAYOUT.md legacy→canonical mapping; `Docs/cli.md` add `profile migrate`.
   - Status entry summarizing the consolidation.

## Acceptance Criteria
- `profile_paths(profile)` returns paths under `config/profiles/<profile>/storageState.json` and `.x-user/<profile>`.
- Direct references to legacy `auth/<profile>/storageState.json` removed from code/scripts (except loaders fallbacks and docs).
- Cookie merges and storage writes succeed with canonical paths; no changes to external behavior.
- Tests pass; repo contracts test reports zero legacy path references in code.

## Risks & Mitigations
- Third-party tooling expecting legacy path: provide optional symlink via migration command; document.
- Subtle path regressions: comprehensive ripgrep sweep + tests.

## Timeline
- Day 0: refactor profiles + cookies writer; migrate a couple of scripts; run tests.
- Day 1: sweep remaining scripts; add migration CLI; docs + contracts test update.

## Metrics
- Count of legacy path references drops to zero in code.
- All state files emitted into `config/profiles` and `artifacts/state` only.
