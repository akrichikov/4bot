# Media, Selector Fallbacks, and Scheduler (Oct 16, 2025)

## Media
- Validation before upload (`xbot/media.py`): size, type (images/video/gif), allow/block flags.
- Config: `MEDIA_MAX_BYTES`, `MEDIA_ALLOW_IMAGES`, `MEDIA_ALLOW_VIDEO`, `MEDIA_ALLOW_GIF`.
- `post-media` uses validation and logs reasons on failure.

## Selector Fallbacks
- Compose textbox widened (`tweetTextarea_` variants).
- Media file input accepts image and video.
- Compose flow adds small fallback focus if textbox missing; waits for media preview.

## Scheduler / Playbooks
- `python -m xbot.cli queue run playbooks/sample.json` runs JSON-defined steps (login/post/like/etc.).
- Global rate limiting still applies; per-step `delay_s` supported.

## Telemetry
- Action logs include media validation summary and artifact paths on failure.

## Violations Check
- No backups; no `/tmp/**`; repo-confined changes.

