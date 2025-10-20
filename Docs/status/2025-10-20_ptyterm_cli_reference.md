## ptyterm / xbot CLI Reference (Operators)

### xbot vterm subcommands

- `vterm http` — start HTTP server; accepts policy/capacity flags:
  - `--allow REGEX` (repeatable), `--deny REGEX` (repeatable); deny has precedence
  - `--max-queue N`, `--rate-qps`, `--rate-burst`, `--audit`, `--admin-token`
- `vterm info` — fetch combined `/version` + `/config` JSON
- `vterm wait` — poll `/health` (or `/ready` with `--ready`) until available
- `vterm console` — open the web console

### Makefile shortcuts

Run `make help-pty` to discover common actions:

```
make pty-http           # start HTTP server
make pty-queue-run      # enqueue echo hello
make pty-queue-wait     # wait for job 1
make pty-admin-restart  # restart shell (admin token)
make pty-admin-resize   # resize PTY 80x24
make pty-version        # GET /version
make pty-config         # GET /config
make pty-metrics        # GET /metrics (truncated)
make vterm-info         # combined /version + /config via xbot
make vterm-wait         # wait for /health
make vterm-console      # open web console
make vterm-snapshot     # write Docs/status/vterm_snapshot.json
```

### Further reading

- `Docs/DEVELOPER_PTYTERM.md` — developer guide for integration
- `Docs/status/2025-10-20_ptyterm_observability.md` — observability cheatsheet
- `Docs/status/2025-10-20_ptyterm_http_policy_and_admin.md` — HTTP policy/admin examples
- `Docs/status/2025-10-20_ptyterm_presets.md` — safe-start preset and example payloads
