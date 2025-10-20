## Input Analysis

- Tree paths affected:
  - Removed: `xbot/static/vterm_console.html`, `xbot/static/vterm_console.js`
  - Source of truth: `submodules/ptyterm/ptyterm/static/{vterm_console.html,vterm_console.js}`

## Synthesis

- Purpose: eliminate duplicate static assets in 4bot; rely on `ptyterm` HTTP server’s embedded static directory.
- Rationale: `ptyterm.vterm_http` serves files from its own package path. Duplicates in 4bot were unused and risked drift.

## Verification

- Search confirms no code paths serve `xbot/static/*`. Tests request `/static/vterm_console.js` from the running `VTermHTTPServer`.
- Re-export modules in `xbot` continue to import from `ptyterm`.

## Outcome

- Duplicates removed; single source in `ptyterm` only.
- No backups created; no `/tmp` usage; no changes outside tree.

