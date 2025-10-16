# Content Confirmation and HTML Auto-Report (Oct 16, 2025)

## Content Confirmation
- Config: `CONFIRM_CONTENT_ENABLED=true` (default) uses selectors `TWEET_TEXT_SELECTORS` to look for posted text.
- Post: records `confirm` meta as `toast+content` | `content` | `toast` | `unknown`.
- Reply: still uses toast confirmation (content check can be added later depending on UI).

## HTML Auto-Report
- Config: `REPORT_HTML_ENABLED=true` optionally with `REPORT_HTML_ACTIONS=post,reply,like,retweet`.
- Auto-generates `artifacts/results/report.html` on each recorded action.
- Report includes action cards, meta, artifact paths, and inline screenshot thumbnails if present.

## Commands
- Manual: `python -m xbot.cli report html --index artifacts/results/index.jsonl --out artifacts/results/report.html --actions post,reply --limit 200`.

## Violations Check
- No backups; no `/tmp/**`; changes confined to repo tree.

