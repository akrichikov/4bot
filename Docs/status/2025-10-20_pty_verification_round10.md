## Input Analysis
- Triads at root and key subfolders.
- Strong scans excluding `submodules/` for PTY primitives/classes and static asset refs.
- Runtime import provenance check for `VTerm`, `VTermHTTPServer`, and `client_request`.

## Verification Results
- No PTY primitives/classes found in 4bot code.
- `VTerm` resolves to `ptyterm.vterm`; `VTermHTTPServer` to `ptyterm.vterm_http`; `client_request` from `ptyterm.vtermd`.
- No `xbot/static` directory; assets are served from `ptyterm/static`.

## Conclusion
- PTY implementation is fully externalized to pty repo. 4bot remains clean (Round 10).
