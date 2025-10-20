Launchd Templates
=================

This directory contains templated launchd plists for local development.

- Replace placeholders like {REPO_ROOT} and {LOG_DIR} before installing.
- Copy the rendered plist to `~/Library/LaunchAgents/`.

Quick usage
-----------

1. Render a template (example using envsubst-compatible variables):

   REPO_ROOT="$(pwd)" \
   LOG_DIR="$(pwd)/logs" \
   X_USER="your-email@example.com" \
   envsubst < com.4botbsc.cz-daemon.template.plist > com.4botbsc.cz-daemon.plist

2. Install:

   launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist 2>/dev/null || true
   cp com.4botbsc.cz-daemon.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist

Troubleshooting
---------------
- Ensure `python3 -m xbot.cli --help` works from your login shell.
- Verify that rendered plists contain no absolute `/Users/` paths.
- Check logs under `logs/` referenced by the plist.
- Unload/reload after edits:

  launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist
  launchctl load ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist

Helper script
-------------

Use the renderer to create plists and optionally install them:

```bash
python -m scripts.launch.install_launchd_from_templates render --var X_USER="name@example.com"
python -m scripts.launch.install_launchd_from_templates install
```
