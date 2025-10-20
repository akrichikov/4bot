#!/bin/bash
# @4botbsc System Status Dashboard
# Quick health check for mention monitoring system

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         @4botbsc Mention Monitor Status Dashboard           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Monitor Process Status
echo "┌─ Monitor Process ─────────────────────────────────────────┐"
if ps aux | grep monitor_mentions.py | grep -v grep > /dev/null; then
    ps aux | grep monitor_mentions.py | grep -v grep | awk '{print "│ ✅ RUNNING - PID: "$2" | Memory: "$6" KB | CPU: "$3"% |"}'
else
    echo "│ ❌ NOT RUNNING - Execute: python monitor_mentions.py &     │"
fi
echo "└────────────────────────────────────────────────────────────┘"
echo ""

# Authentication Status (resolve via Python helpers)
echo "┌─ Authentication ──────────────────────────────────────────┐"
COOKIE_COUNT=$(python - <<'PY'
from xbot.profiles import storage_state_path
from pathlib import Path
import json
p = storage_state_path('4botbsc')
try:
    data = json.loads(Path(p).read_text())
    print(len(data.get('cookies', [])))
except Exception:
    print(0)
PY
)
if [ "$COOKIE_COUNT" -gt 0 ] 2>/dev/null; then
    echo "│ ✅ Cookies: $COOKIE_COUNT tokens loaded                           │"
else
    echo "│ ❌ No valid auth cookies found                                │"
fi
echo "└────────────────────────────────────────────────────────────┘"
echo ""

# Reply History (resolve path via Config)
echo "┌─ Reply History ───────────────────────────────────────────┐"
REPLY_COUNT=$(python - <<'PY'
from xbot.config import Config
from pathlib import Path
import json
cfg = Config.from_env()
p = Path(cfg.artifacts_dir) / 'state' / 'replied_mentions.json'
print(len(json.loads(p.read_text())) if p.exists() else 0)
PY
)
echo "│ 📊 Total Replies: ${REPLY_COUNT} mentions                            │"
echo "└────────────────────────────────────────────────────────────┘"
echo ""

# Resource Usage
echo "┌─ Resource Usage ──────────────────────────────────────────┐"
PLAYWRIGHT_COUNT=$(ps aux | grep "playwright/driver/node" | grep -v grep | wc -l | tr -d ' ')
if [ "$PLAYWRIGHT_COUNT" -gt 0 ]; then
    echo "│ ⚠️  Orphaned Processes: $PLAYWRIGHT_COUNT (run cleanup)              │"
else
    echo "│ ✅ Orphaned Processes: 0 (optimal)                         │"
fi
echo "└────────────────────────────────────────────────────────────┘"
echo ""

# Documentation
echo "┌─ Quick Commands ──────────────────────────────────────────┐"
echo "│ View logs:     tail -20 Docs/status/mention_monitor.log   │"
echo "│ Stop monitor:  pkill -f monitor_mentions.py               │"
echo "│ Start monitor: python -m scripts.monitor.monitor_mentions & │"
echo "│ Test reply:    python -m apps.cz.reply_to_mention           │"
echo "│ Re-auth:       xbot login --profile 4botbsc               │"
echo "└────────────────────────────────────────────────────────────┘"
echo ""

echo "Last checked: $(date '+%Y-%m-%d %H:%M:%S')"
