
## Input Analysis

- Ran: `pwd && ls -la` and a tree listing (depth 2) from repo root.
- Performed exhaustive ripgrep to detect any direct PTY implementation (import pty, termios, tty, openpty, TIOCSWINSZ) outside `submodules/ptyterm`.

## Synthesis

- xbot static duplicates removed earlier; now removed empty directory `xbot/static/` to avoid confusion.
- Re-export stubs in `xbot/vterm*.py` point exclusively to `ptyterm.*` and include robust fallback to submodule shim.

## Verification

- No direct PTY code found outside `submodules/ptyterm/ptyterm/*`.
- Matches only in CLI wrappers, docs, tests, and re-export modules.
- Confirmed `/console` and `/health` functional via `xbot.cli vterm http`.

## Output

- PTY implementation present only in pty repo/submodule.
- No backups created; no /tmp usage; no duplicates remain.
