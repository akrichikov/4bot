# 2025-10-16 — CZ Mention→VTerm→RabbitMQ→Reply Pipeline (Headless)

## Summary
- Headless notifications subscriber filters only @4botbsc mentions.
- Sends JSON to VTerm HTTP queue to craft CZ replies.
- Publishes replies to RabbitMQ request queue (durable).
- Reply consumer posts headlessly in a fresh authenticated tab, cleans up the tab, and reports completion on response queue.
- launchd plists added for background services.

## Components
- Notifications: `cz_vterm_rabbitmq_daemon.py` (NotificationMonitor, TabManager).
- VTerm HTTP: `xbot/vterm_http.py` (queue `/queue/run`, `/queue/{id}`); plist `com.4botbsc.vterm-http.plist`.
- RabbitMQ: `rabbitmq_manager.py` ensures durable exchange/queues/bindings.
- Reply posting: `RabbitMQBridge.start_reply_consumer()` + `post_reply_to_twitter()`.

## Launch
1. Start VTerm HTTP: `launchctl load ~/Library/LaunchAgents/com.4botbsc.vterm-http.plist`
2. Start CZ Daemon: `launchctl load ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist`
3. Logs:
   - `logs/vterm_http.out.log`, `logs/vterm_http.err.log`
   - `logs/cz_daemon.out.log`, `logs/cz_daemon.err.log`

## Auth (Headless)
- Cookies: `auth_data/x_cookies.json`
- Storage: `config/profiles/4botbsc/storageState.json`
- Fallback creds: `.env` (`x_user`, `x_passwd`); TOTP via `X_TOTP_SECRET` if needed.

## RabbitMQ Topology
- Exchange: `4botbsc_exchange` (topic, durable)
- Queues: `4bot_request`, `4bot_response` (durable)
- Bindings: `4bot.request.*`, `4bot.response.*`

## Status
- Pipeline wired and ready. Use X mentions to trigger end-to-end flow.

