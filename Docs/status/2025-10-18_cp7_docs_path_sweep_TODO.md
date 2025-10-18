# Critical Path 7: Docs Path Sweep, REPO Layout, and Guidance

## Objectives
- Align all documentation with the new multi-level repository layout and path conventions.
- Remove or quarantine absolute machine-specific paths; provide canonical, parameterized path references.
- Establish a durable, discoverable documentation hub and style guidance to prevent future drift.

## Deliverables
- New hub doc: `Docs/REPO_LAYOUT.md` with a living map of directories, purposes, and key files.
- Path migration appendix: legacy → canonical mapping table used across docs.
- Updated guides: launchd usage (post‑CP2), logging (post‑CP3), CLI (post‑CP4), dev setup (post‑CP6).
- Lint/check script to flag absolute paths and unapproved root-level references in docs.
- Status note summarizing the sweep and policy going forward.

## Design
- REPO_LAYOUT.md structure:
  - Overview: high-level goals and invariants (no artifacts at repo root; logs/ and artifacts/ only).
  - Directory catalog: `xbot/`, `apps/`, `scripts/` (`auth, launch, manual, monitor, notification, orchestrator, rabbitmq, shell`), `bin/launchd/`, `config/monitor`, `artifacts/{state,results,screens,misc}`, `logs/`…
  - Key files and responsibilities; do/do‑not rules (e.g., no absolute paths; use `{REPO_ROOT}`).
  - Path macros: `{REPO_ROOT}`, `{LOGS_DIR}`, `{ARTIFACTS_DIR}`, `{STATE_DIR}`, `{RESULTS_DIR}`, `{SCREENS_DIR}`, `{PROFILES_DIR}`.
  - Legacy mapping appendix: examples of old → new references for common tasks.
- Documentation conventions:
  - Use placeholders/macros in prose/code blocks; provide a short preface that maps them to real paths (e.g., `export REPO_ROOT=$(pwd)`).
  - Prefer relative paths rooted at repo; shell code fences should `cd "$REPO_ROOT"`.
  - For user secrets/env, refer to `.env` keys; never inline secrets.
- Lint/check script scope:
  - Reject `/Users/...`, `C:\\...` absolute paths; warn on raw `replied_mentions.json` without `artifacts/state` prefix.
  - Emit a per‑file report with offending lines and a suggested fix.

## Task Breakdown
1) Author `Docs/REPO_LAYOUT.md`
   - Include directory tree snapshot and purpose bullets.
   - Define and document path macros and invariants.
   - Provide migration examples (legacy → canonical).
2) Update core guides
   - launchd: reflect generator usage (CP2) and logs under `logs/`; remove copy‑plist steps.
   - logging: link to CP3 decisions; show tail commands; audit JSONL path.
   - cli: list new `ops/monitor/verify/launchd/config` commands; examples with flags.
   - dev_setup: bootstrap with `make dev`, Playwright install, pre‑commit.
3) Quarantine legacy absolutes
   - Add banner to historical status docs that predate the reorg: “Legacy Paths — preserved for audit; see REPO_LAYOUT.md for current paths.”
   - Do not rewrite historical logs; add a small header note only.
4) Write doc‑lint script
   - `scripts/orchestrator/doc_lint.py`: scan `Docs/**/*.md` for disallowed patterns (`/Users/...`, `replied_mentions.json` not under `artifacts/state`, `cp *.plist` at root).
   - Exit non‑zero when violations found; print human‑readable suggestions citing macros.
   - Add `make doc-lint` target.
5) Index and navigation
   - Add `Docs/index.md` linking to REPO_LAYOUT.md, cli.md, launchd.md, logging.md, dev_setup.md, status/.
   - Optionally add a brief pointer in the root README (if present).

## Acceptance Criteria
- All “how‑to” docs use canonical paths/macros; examples runnable by `cd "$REPO_ROOT"` and copy‑paste.
- Legacy status documents remain unmodified except for a clearly labeled banner.
- Doc lint returns clean; helper script present and wired to Makefile.

## Risks & Mitigations
- Over‑editing status history: use banner approach only; never rewrite logs.
- Future drift: path macros + doc‑lint + REPO_LAYOUT.md as single source-of-truth minimize divergence.

## Timeline
- Day 0: REPO_LAYOUT.md, doc‑lint script, update launchd/logging/cli guides; status banner template.
- Day 1: dev setup doc, Docs/index.md, Make hooks; run doc‑lint and sweep stragglers.

## Metrics
- doc‑lint violations trend to zero.
- Readme-to-setup time drops; fewer “path not found” support issues.
