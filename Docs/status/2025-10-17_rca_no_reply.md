# RCA: Bot Did Not Reply to Mention (2025-10-17)

## Summary
- The reply pipeline detected and generated a reply for the mention, but posting to X did not occur due to an invalid/expired authenticated session (Playwright storageState not recognized as logged-in).

## Evidence
- VTerm proxy processed request and published generated reply (see `logs/vterm_proxy.log`).
- Response queue `4bot_response` has an active consumer (verify via `rabbitmq_setup.py`), but no "Reply posted" events appear in logs.
- Auth verification shows not logged in:
  - Ran: `python3 verify_auth.py`
  - Result: `Authentication INVALID - User is NOT logged in`.

## Root Cause
- Invalid/expired authentication state at `config/profiles/4botbsc/storageState.json` (and/or `auth/4botbsc/storageState.json`).
- As a result, the reply poster cannot navigate and submit replies even when a generated reply arrives via RabbitMQ.

## Contributing Factors
- Multiple pipelines (daemonized vs. modular) with mixed routing keys can obscure which consumer is responsible for posting.
- No explicit error persisted from the reply poster; success/failure not visible in current logs beyond initialization.

## Corrective Actions
1. Refresh authentication
   - `python3 fresh_login.py`
   - Complete login in the visible browser; press ENTER to save.
   - Verify: `python3 verify_auth.py` → should report `Authentication VALID`.
2. Ensure consumers are running
   - VTerm HTTP server: `curl http://127.0.0.1:8765/health` → `{ "ok": true }`.
   - VTerm proxy manager: `python3 vterm_request_proxy_manager.py` (tmux/bg/LaunchAgent).
   - Reply poster (one of):
     - `python3 cz_reply_manager.py` (consumes `cz_reply_generated` from `4bot_response`).
     - or `python3 cz_reply_poster.py`.
3. Re-enqueue reply for the tweet
   - Quick path: `python3 reply_to_mention.py` (uses storageState and posts directly).
   - Queue path: small snippet to call `RabbitMQManager.publish_cz_reply_request(post_url=..., author_handle=..., content=...)` and let the proxy + poster handle it.

## Verification
- Observe `logs/cz_reply_poster.log` or console for:
  - `📥 Received generated CZ reply`
  - `✅ Reply posted`
- Confirm on X the reply appears under the tweet.

## Preventive Measures
- Add a startup auth check in reply poster: exit early with clear error if `verify_auth` fails.
- Emit structured logs for post attempts and failures (HTTP status, UI selector failures, screenshots saved path).
- Optional: daily cron to refresh storageState or alert when invalid.

## Status
- Pending: Await fresh login + rerun poster to confirm end-to-end success.
