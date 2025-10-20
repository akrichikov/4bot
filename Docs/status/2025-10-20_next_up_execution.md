## Input Analysis

- Objective: finalize standalone `ptyterm` integration without remote push dependency.
- Constraints: single-source in submodule; zero duplication; preserve tests; CI must install ptyterm.

## Synthesis (TODOs via sequential thinking)

1) Makefile bootstrap for `ptyterm` (submodules-init, deps-pty).
2) CI: checkout submodules; pip install -e submodules/ptyterm before project deps.
3) Health workflow: same as CI for submodules and install.
4) Friendly error if `ptyterm` missing (re-export modules raise with fix hint).
5) Verify vterm tests locally.

## Output / Implementation Notes

- Added Makefile targets: `submodules-init`, `deps-pty`.
- CI workflows now: `actions/checkout@v4` with `submodules: true`; install editable submodule package.
- Health workflow mirrors CI bootstrap.
- Re-export modules (`xbot/vterm*.py`) now raise informative ImportError if `ptyterm` not installed.
- Local verification: `pytest -q -k "vterm and not live"` PASS.

## Next Up (blocked on remote URL)

- Add remote to `/Users/doctordre/projects/pty` and push `main`.
- Update `.gitmodules` to point to remote URL; `git submodule sync`; commit.

