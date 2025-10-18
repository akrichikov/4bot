# 2025-10-18 Orchestrator Simulation (run-sim)

## Overview
Runs a dry-run orchestrator that uses the fair scheduler to process per-profile queues. Useful for tuning `rps`, `burst`, and quiet hours before wiring into live pipelines.

## Make target
- `make schedule-run-sim PROFILES="a:1:10;b:2:10" ITEMS="a=100;b=50" SIM_SECONDS=30 SIM_DT_MS=50 QUIET="a=22:00-06:00"`
  - Output: `Docs/status/scheduler_run.json`

## Parameters
- `PROFILES` (required): `name:rps:burst;name2:rps:burst`
- `ITEMS` (required): `name=count;name2=count`
- `SIM_SECONDS` (optional): duration seconds (default: 30)
- `SIM_DT_MS` (optional): time step in milliseconds (default: 50)
- `QUIET` (optional): `name=HH:MM-HH:MM,name2=...` (supports overnight windows)

## Notes
- Pure offline simulation (no MQ/browser). Deterministic and fast.
- Combine with `make status-aggregate` and `make status-index` (or `make site-all`) to include results in the status site.
