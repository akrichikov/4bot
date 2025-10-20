## ptyterm Presets

### Safe Start (deny destructive commands)

Make target: `make pty-http-safe PTY_PORT=9876 PTY_ADMIN=adm`

Flags used:

- `--deny 'rm'` — blocks commands containing `rm`
- `--deny 'shutdown'`, `--deny 'reboot'` — blocks obvious system shutdowns
- `--deny ':\(\)\{:\|:&\};:'` — blocks the classic fork bomb pattern
- `--max-queue 4` — limits concurrent in‑flight jobs
- `--audit` — writes JSONL audit entries if configured
- `--admin-token adm` — protects admin endpoints

Override any flag by invoking `python -m ptyterm vterm http` directly or editing the Makefile target as needed.

### Quick test payload

Create `Docs/status/payloads/run_echo.json` with:

```json
{ "cmd": "echo preset-ok" }
```

Then:

```bash
python -m xbot.cli vterm curl POST /run \
  --base http://127.0.0.1:9876 \
  --data-file Docs/status/payloads/run_echo.json
```

