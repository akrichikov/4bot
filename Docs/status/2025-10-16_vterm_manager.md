# 2025-10-16 — In‑Memory PTY Virtual Terminal Manager

## Summary
- Added `xbot/vterm.py`: in-memory PTY terminal manager that launches a shell, supports free-form writes, and returns structured JSON on reads.
- Added tests `tests/test_vterm.py`: validate echo, JSON extraction, key/value parsing, and simple table parsing.
- Default shell: `/bin/bash` (falls back to `$SHELL` or `/bin/sh`); normalizes prompts for stable parsing.

## API
- `VTerm.start()` — initialize PTY shell.
- `VTerm.write(text: str)` — free-form write to terminal.
- `VTerm.run(command: str, timeout: float = 10.0) -> VTermResult` — execute command; returns structured extraction with `exit_code`, `lines`, `json_objects`, `key_values`, `table`, `stats`.
- `VTerm.read_structured(timeout: float = 0.1) -> VTermResult` — read any available output and parse.
- `VTerm.close()` — terminate shell.

## Structured Extraction
- JSON: whole-text or line-wise JSON objects/arrays.
- Key/Value: `key=value` and `key: value` pairs.
- Table: first line headers + rows split on 2+ spaces.
- Always includes `raw_text`, `lines`, and `stats` (bytes, lines, elapsed_ms).

## Validation
- `pytest -q -k 'not browser_cookie_test'` → green.

## Paths
- `xbot/vterm.py:1`
- `tests/test_vterm.py:1`

## Notes
- Prompts are normalized (PS1, PS2); ANSI stripped; secondary prompts (PS2) pre/suffix removed.
- Here-docs work, but tests prefer quoting/printf for portability.
