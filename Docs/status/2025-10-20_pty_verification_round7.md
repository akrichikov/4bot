## Input Analysis
- Ran triads (pwd, ls, tree) at root and key subfolders.
- Searched excluding `submodules/` for PTY primitives and class/daemon/server markers.

## Verification Results
- No PTY primitives or class implementations found in 4bot.
- Only re-export/import usage in `xbot/vterm*.py` and consumer code.
- `xbot/static` remains absent; assets are sourced from `ptyterm/static`.

## Conclusion
- PTY implementation is 100% externalized to the pty repo; 4bot is clean (Round 7).
