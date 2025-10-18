# 2025-10-18 Status Site Pipeline Update

## New Make targets

- `guardrails` – evaluate reply safety if an input file is provided.
  - Usage: `make guardrails GUARD_IN=Docs/status/sample_replies.txt`
  - Output: `Docs/status/guardrail_eval.json`

- `schedule-sim` – run the fair scheduler simulation and record counts.
  - Usage: `make schedule-sim PROFILES="a:1:10;b:2:10" SIM_SECONDS=10 SIM_DT_MS=100`
  - Output: `Docs/status/scheduler_sim.json`

- `status-aggregate` – aggregate health, guardrails, and scheduler into one JSON.
  - Usage: `make status-aggregate`
  - Output: `Docs/status/status_summary.json`

- `site-all` – full pipeline: health → (optional) guardrails → (optional) schedule sim → aggregate → index.
  - Usage: `make site-all GUARD_IN=Docs/status/sample_replies.txt PROFILES="a:1:10;b:2:10"`
  - Outputs: health JSON/HTML, guardrail_eval.json, scheduler_sim.json, status_summary.json, index.html

## Notes
- Optional steps are skipped when inputs are not provided; messages indicate skipped actions.
- The System Health HTML now includes a Guardrails card when `guardrail_eval.json` is present.
- The index lists all JSON/HTML under `Docs/status/` automatically.
