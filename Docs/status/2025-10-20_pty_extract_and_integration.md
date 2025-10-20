## Input Analysis

- CWD: `/Users/doctordre/projects/4bot`
- Commands executed (pre-exec due diligence):
  - `pwd && ls -1a` (ok)
  - `tree -a -I ".git|.venv|__pycache__|.pytest_cache|node_modules|dist|build|*.egg-info" -n -L 2` (ok)
- PTY/VTerm code and docs identified (single source truths):
  - Code: `xbot/vterm.py`, `xbot/vtermd.py`, `xbot/vterm_http.py`, `xbot/vterm_client.py`
- Assets now live only in `ptyterm/static/{vterm_console.html,vterm_console.js}` (4bot duplicates removed on 2025-10-20 to enforce single source of truth)
  - CLI integration (re-exports): `xbot/cli.py` uses `vterm`/`vtermd`/`vterm_http`
  - Apps (consumers): `apps/cz/vterm_request_proxy_manager.py`, `apps/cz/vterm_cz_integration.py`, `apps/cz/cz_vterm_rabbitmq_daemon.py`
  - Tests: all `tests/test_vterm*` and `tests/test_vtermd*`, plus HTTP/WS queue tests
  - Docs: `Docs/status/2025-10-16_vterm_keepalive_singleton.md`, `Docs/status/2025-10-17_cz_vterm_rabbitmq_daemon.md`, launchd templates, related status logs

## Synthesis

- Designed new standalone repo at `/Users/doctordre/projects/pty` with package `ptyterm`:
  - `ptyterm/vterm.py`, `ptyterm/vtermd.py`, `ptyterm/vterm_http.py`, `ptyterm/vterm_client.py`
  - `ptyterm/static/{vterm_console.html,vterm_console.js}`
  - `pyproject.toml` (aiohttp runtime dep), `README.md`
- Git initialized and committed (`main`).
- Installed into 4bot’s virtualenv as editable: `.venv/bin/pip install -e /Users/doctordre/projects/pty`.
- In 4bot, replaced implementations with thin re-exports to enforce single source of truth:
  - `xbot/vterm.py` → `from ptyterm import VTerm, VTermResult`
  - `xbot/vtermd.py` → `from ptyterm.vtermd import VTermDaemon, client_request, DEFAULT_SOCKET`
  - `xbot/vterm_http.py` → `from ptyterm.vterm_http import VTermHTTPServer`
  - `xbot/vterm_client.py` → `from ptyterm.vterm_client import VTermClient`
- Added submodule: `git submodule add /Users/doctordre/projects/pty submodules/ptyterm` (committed).
- Tests:
  - Collect-only (vterm scope): PASS.
  - Runtime (vterm scope): PASS (`.venv/bin/pytest -q -k "vterm and not live"`).

## Identified Paths

- New repo: `/Users/doctordre/projects/pty`
- Submodule path (read-only vendor reference): `submodules/ptyterm`
- Runtime import path: Installed package `ptyterm` in project `.venv`
- Re-export stubs: `xbot/vterm.py`, `xbot/vtermd.py`, `xbot/vterm_http.py`, `xbot/vterm_client.py`

## Verification

- Duplicates: none (logic lives only in `ptyterm`; 4bot files re-export).
- Backups: none created.
- `/tmp`: not used.
- Clean imports: vterm-related tests collected and executed successfully.

## Clarification Required

- Remote repository URL for `/Users/doctordre/projects/pty` is required to complete:
  - `git remote add origin <GITHUB_URL>`
  - `git push -u origin main`
- After remote is set, I can update the submodule to point to the remote URL (instead of local file transport), commit, and (optionally) push 4bot.

## Next Steps (upon remote provided)

1. Set remote on `pty` and push: `git -C /Users/doctordre/projects/pty remote add origin <url>; git -C /Users/doctordre/projects/pty push -u origin main`.
2. Update submodule URL: `git config -f .gitmodules submodule.submodules/ptyterm.url <url>; git submodule sync; git add .gitmodules; git commit -m "chore: point ptyterm submodule to remote"`.
3. Optional: CI pinning/versioning for `ptyterm` and add packaging constraints.

## Output

- Global Success criteria (phase):
  - Extraction complete ✅
  - Standalone repo structured, committed ✅
  - Submodule added and integrated ✅
  - Tests (vterm scope) pass with 0 errors/warnings ✅
  - Pending: push new repo to remote (needs URL) ⏸️
