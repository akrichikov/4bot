## Input Analysis
- Triads (pwd, ls, tree) at root and subfolders.
- Strong scans excluding `submodules/` for PTY primitives/classes and static refs.
- Runtime provenance verified for core symbols.

## Verification Results
- No PTY primitives/classes/daemon implementations in 4bot code.
- Core symbols resolve to `ptyterm.*` modules.
- `xbot/static` remains absent; static assets are in `ptyterm/static`.

## Conclusion
- PTY implementation remains fully centralized in pty repo. 4bot remains clean (Round 28).
