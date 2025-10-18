# Status Artifacts

- Generate health reports and index:
  - `make system-health-html` – writes `Docs/status/system_health.(json,html)`
  - `make status-index` – writes `Docs/status/index.html`
  - `make site` – runs both of the above
  - `make site-open` – opens the status index in your default browser

- Strict health (non-blocking):
  - `make health-strict` – runs `xbot health system --strict` and writes JSON; returns non-zero if any gate fails (guarded with `|| true` in the Makefile to avoid breaking your shell).

These commands operate only within the repository and do not use /tmp. The index is non-recursive and lists only top-level HTML/JSON files in `Docs/status`.
