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

# Authentication Status
echo "┌─ Authentication ──────────────────────────────────────────┐"
if [ -f "auth/4botbsc/storageState.json" ]; then
    COOKIE_COUNT=$(jq '.cookies | length' auth/4botbsc/storageState.json 2>/dev/null)
    echo "│ ✅ Cookies: $COOKIE_COUNT tokens loaded                           │"
else
    echo "│ ❌ No auth file found                                         │"
fi
echo "└────────────────────────────────────────────────────────────┘"
echo ""

# Reply History
echo "┌─ Reply History ───────────────────────────────────────────┐"
if [ -f "replied_mentions.json" ]; then
    REPLY_COUNT=$(jq 'length' replied_mentions.json 2>/dev/null)
    echo "│ 📊 Total Replies: $REPLY_COUNT mentions                            │"
else
    echo "│ 📊 Total Replies: 0 (file will be created on first reply)  │"
fi
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
