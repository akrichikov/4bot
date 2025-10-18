Title: Launch/Shell Artifacts Normalized; Makefile commands added
Date: 2025-10-18

Summary
- Launchers and shell scripts now use module execution and repo-relative paths.
- LaunchAgents: cz-daemon uses `python3 -m apps.cz.cz_vterm_rabbitmq_daemon`; vterm-http already uses `python3 -m xbot.cli vterm http`.
- Scripts now reference local files (Docs, logs, auth) without absolute paths.
- Makefile expanded with commands for cz-proxy, cz-daemon, notifications, start-all, stop-all.

Changes
- launch_tweet_replies.sh:
  - CD to repo root dynamically; PYTHONPATH from `pwd`.
  - Count URLs from `Docs/4Bot Tweets.md`.
  - Execute `python3 -m apps.cz.cz_reply_to_tweets`.
- status_dashboard.sh:
  - Relative checks for auth and replied mentions.
  - Module invocation examples for monitor and reply test.
- com.4botbsc.cz-daemon.plist:
  - ProgramArguments switched to module form (`-m apps.cz.cz_vterm_rabbitmq_daemon`).
- Makefile:
  - Added cz-proxy, cz-daemon, notifications, start-all, stop-all.
  - Format target includes apps and scripts directories.

Verification
- pytest -q → green (1 skip).
- Grep for user-absolute paths in Python code minimized; remaining absolute paths only in logs/docs/historical and vterm-http LaunchAgent (WorkingDirectory kept absolute for reliability).
