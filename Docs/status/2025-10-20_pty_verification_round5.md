## Input Analysis
- Executed `pwd && ls -la` and `tree -a -L 2` at repo root and key subdirs.
- Ran scans excluding `submodules/` for PTY primitives and server/daemon classes.

## Verification Results
- No PTY implementation in 4bot outside `submodules/ptyterm/ptyterm/*`.
- Re-export stubs only; xbot/static absent.
- Removed transient debug files (server.err/pid variants) for hygiene.

## Conclusion
- PTY implementation remains fully centralized in the pty repo. 4bot is clean.
