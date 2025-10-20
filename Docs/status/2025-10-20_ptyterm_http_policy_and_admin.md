## ptyterm HTTP Policy, Capacity, and Admin Endpoints

### Policy Controls

- `--allow REGEX` (repeatable): allow commands matching any regex. If omitted, all commands are allowed by default.
- `--deny REGEX` (repeatable): deny commands matching any regex. Deny takes precedence over allow.

The server responds with `403 {"error":"forbidden"}` when a command is blocked.

### Queue Capacity

- `--max-queue N`: limits in-flight jobs (pending + running). When full, `POST /queue/run` returns `429 {"error":"queue_full"}`.
- `GET /queue/stats`: returns counts (`pending`,`running`,`done`,`error`,`inflight`) and `capacity` when set.

### Admin Endpoints (require `--admin-token`)

- `GET /ready` → `{ ok:true, alive:<bool> }`
- `POST /admin/restart` with header `X-VTerm-Admin: <token>` → restarts shell.
- `POST /admin/resize` with header + JSON body `{"rows":24,"cols":80}` → resizes PTY.
- `POST /admin/shutdown` → exits process.

### Examples

```bash
# Start server with policy, capacity, and admin token
ptyterm vterm http \
  --port 9876 \
  --allow '^echo\\b' \
  --deny 'rm\\s+-rf' \
  --max-queue 4 \
  --admin-token adm

# Admin: resize to 80x24
curl -s -X POST -H 'X-VTerm-Admin: adm' \
  -H 'content-type: application/json' \
  -d '{"rows":24,"cols":80}' \
  http://127.0.0.1:9876/admin/resize | jq

# Queue: run + wait
ptyterm queue run echo hello --target http://127.0.0.1:9876 | jq
ptyterm queue wait 1 --target http://127.0.0.1:9876 --timeout 5 | jq

# Stats
curl -s http://127.0.0.1:9876/queue/stats | jq
```

