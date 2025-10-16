# Artifacts on Error and Status URL Resolution (Oct 16, 2025)

## Summary
- Per-action trace/HAR naming via Browser label.
- Error screenshots + HTML dumps saved under `artifacts/`.
- Status URL resolver accepts raw IDs or partial paths.

## Implementation
- `xbot/browser.py`: `Browser(cfg, label=...)` sets per-action `trace.zip` and `*.har` filenames.
- `xbot/artifacts.py`: `capture_error()` saves `artifacts/screens/<label>_timestamp.png` and `artifacts/html/<label>_timestamp.html`.
- `xbot/facade.py`: wraps actions with try/except to capture artifacts; `_to_status()` resolves inputs:
  - `1234567890` → `${BASE}/i/web/status/1234567890`
  - `/user/status/123` → `${BASE}/user/status/123`
  - `https://...` left unchanged

## Usage
- Enable tracing/HAR in `.env` to capture per-action archives.
- On failures, inspect `artifacts/screens/` and `artifacts/html/` for context.

## Violations Check
- No backups; no `/tmp/**`; within repo tree only.

