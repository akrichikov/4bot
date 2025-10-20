## ptyterm Integration (Developer Guide)

This repo depends on the standalone `ptyterm` toolkit for all PTY/VTerm functionality.

### Bootstrap

```bash
make submodules-init
make deps-pty
```

Alternatively via CLI:

```bash
python -m xbot.cli deps pty-install
python -m xbot.cli deps pty-verify
```

### Inspect a running VTerm HTTP

```bash
# Print combined /version and /config JSON (exit 1 on failure)
python -m xbot.cli vterm info --base http://127.0.0.1:9876 --timeout 3

# Write JSON to file
python -m xbot.cli vterm info --base http://127.0.0.1:9876 --out Docs/status/vterm_http_info.json
```

### Wait for readiness & open console

```bash
# Wait until /health is OK (exit 1 on timeout)
python -m xbot.cli vterm wait --base http://127.0.0.1:9876 --timeout 5

# Require /ready (shell alive)
python -m xbot.cli vterm wait --base http://127.0.0.1:9876 --ready --timeout 5

# Open browser console
python -m xbot.cli vterm console --base http://127.0.0.1:9876

### Snapshot (version/health/config/metrics excerpt)

```bash
# Using Make target (writes Docs/status/vterm_snapshot.json)
make vterm-snapshot PTY_PORT=9876

# Or script directly
VT_BASE=http://127.0.0.1:9876 python -m scripts.monitor.vterm_snapshot
```

### Environment variables

You can export or `source .env` to propagate defaults used by Makefile targets and snapshot scripts:

```bash
export PTY_PORT=9876       # HTTP port for the server
export PTY_ADMIN=adm       # admin token for /admin endpoints
export VT_BASE=http://127.0.0.1:9876
```

### Remote Sync (optional)

Attach your ptyterm local repo to a remote and repoint the submodule URL:

```bash
make pty-remote-sync URL=git@github.com:YOURORG/ptyterm.git
```

### CI Notes

CI installs `ptyterm` from the submodule if present. If the submodule is not available, it falls back to installing a released version that satisfies `ptyterm>=0.1.0`.
### Run VTerm HTTP from xbot with policy/capacity

```bash
python -m xbot.cli vterm http \
  --port 9876 \
  --allow '^echo' \
  --deny 'rm' \
  --max-queue 4 \
  --rate-qps 5 --rate-burst 5 \
  --audit --admin-token adm
```
### Generic endpoint helper (curl)

```bash
# GET /health
python -m xbot.cli vterm curl GET /health --base http://127.0.0.1:9876

# POST /run with inline JSON
python -m xbot.cli vterm curl POST /run --base http://127.0.0.1:9876 --data '{"cmd":"echo ok"}'

# POST /run with payload from file
python -m xbot.cli vterm curl POST /run --base http://127.0.0.1:9876 --data-file payload.json
```
### Admin helpers

```bash
# Restart the PTY shell
python -m xbot.cli vterm admin-restart --base http://127.0.0.1:9876 --admin-token adm

# Resize the PTY shell to 80x24
python -m xbot.cli vterm admin-resize --base http://127.0.0.1:9876 --admin-token adm --rows 24 --cols 80
```
