Title: Cookie and Auth Unification Across CZ Scripts
Date: 2025-10-18

Summary
- Introduced `xbot.cookies.load_cookies_best_effort(profile)` to centralize cookie discovery and normalization.
- Updated CZ scripts to use centralized cookie loading and merged storage handling where applicable.

Changes
- apps/cz/cz_notification_monitor.py: Uses load_cookies_best_effort when AUTH_MODE=cookies.
- apps/cz/cz_reply_poster.py: Replaced ad-hoc cookie aggregation with load_cookies_best_effort.
- apps/cz/cz_headless_batch.py: Merges cookies into storage via load_cookies_best_effort + merge_into_storage.
- apps/cz/reply_to_mention.py: Delegates cookie loading to load_cookies_best_effort.
- apps/cz/cz_targeted_replies.py: Merges cookies via centralized helper.
- apps/cz/cz_mass_reply.py: Same as above.
- apps/cz/cz_tweet_poster.py: Same as above.

Verification
- pytest -q: green (1 skip).
- Grep scans show removal of duplicated cookie-loading logic and absolute paths.

Notes
- Remaining pipeline pieces already supported by module execution and centralized config in previous steps.
