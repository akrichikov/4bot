# @4botbsc Mention Monitor - Quick Reference Card

## System Status
**Current Status:** ✅ **LIVE**
**Monitor PID:** 99514
**Memory Usage:** ~34MB
**Check Interval:** Every 15 minutes
**Last Started:** 2025-10-17 02:17 UTC

## Quick Commands

### Status Check
```bash
# Verify monitor is running
ps aux | grep monitor_mentions.py | grep -v grep

# Quick status with details
ps aux | grep monitor_mentions.py | grep -v grep | awk '{print "PID: "$2", Memory: "$6", Runtime: "$9}'

# Check recent activity
tail -20 /Users/doctordre/projects/4bot/Docs/status/mention_monitor.log

# View reply history
cat /Users/doctordre/projects/4bot/replied_mentions.json | jq .
```

### Control Commands
```bash
# Stop the monitor
pkill -f monitor_mentions.py

# Start the monitor (continuous mode)
cd /Users/doctordre/projects/4bot
nohup python monitor_mentions.py > Docs/status/mention_monitor.log 2>&1 &

# Run one-time check (for testing)
python monitor_mentions.py --once

# Check for new mentions without continuous loop
python monitor_mentions.py --once 2>&1 | grep "New mention"
```

### Authentication Management
```bash
# Re-authenticate with xbot CLI
cd /Users/doctordre/projects/4bot
xbot login --profile 4botbsc --browser webkit

# Sync cookies after re-authentication
cp auth/4botbsc/storageState.json config/profiles/4botbsc/storageState.json

# Verify authentication
python test_auth_correct_path.py
```

### Manual Reply Operations
```bash
# Reply to specific mention (edit tweet_url and response in file first)
python reply_to_mention.py

# Test reply to hardcoded tweet
python reply_to_mention.py
# Default: https://x.com/krichikov10228/status/1978870565835542864
# Response: "4. BUIDL > FUD"
```

## File Locations

| File | Purpose | Location |
|------|---------|----------|
| Monitor Script | Main loop | `/Users/doctordre/projects/4bot/monitor_mentions.py` |
| Reply Script | Single tweet | `/Users/doctordre/projects/4bot/reply_to_mention.py` |
| Auth Test | Verify login | `/Users/doctordre/projects/4bot/test_auth_correct_path.py` |
| Reply History | Tracking | `/Users/doctordre/projects/4bot/replied_mentions.json` |
| Monitor Log | Output | `/Users/doctordre/projects/4bot/Docs/status/mention_monitor.log` |
| Primary Cookies | xbot auth | `/Users/doctordre/projects/4bot/auth/4botbsc/storageState.json` |
| Secondary Cookies | Scripts | `/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json` |
| Deployment Doc | Full guide | `/Users/doctordre/projects/4bot/Docs/status/mention_monitoring_deployment.md` |

## Monitoring Workflow

```
Every 15 minutes:
  1. Monitor wakes up
  2. Loads webkit browser (headless)
  3. Navigates to x.com/notifications/mentions
  4. Parses first 10 mention tweets
  5. Checks each tweet_id against replied_mentions.json
  6. For new mentions:
     - Opens tweet URL (non-headless)
     - Clicks reply button
     - Types CZ-style response
     - Submits with Control+Enter
     - Saves tweet_id to prevent duplicates
     - Waits 10s before next reply
  7. Sleeps for 15 minutes
  8. Repeat
```

## CZ Response Styles
```python
[
    "4",
    "4.",
    "4. BUIDL > FUD",
    "4. We keep building.",
    "4. Focus on the work.",
    "BUIDL.",
]
```

## Troubleshooting

### Monitor Not Responding
```bash
# Kill and restart
pkill -f monitor_mentions.py
sleep 2
cd /Users/doctordre/projects/4bot
nohup python monitor_mentions.py > Docs/status/mention_monitor.log 2>&1 &
```

### Authentication Expired
```bash
# Check auth
python test_auth_correct_path.py

# If failed, re-login
xbot login --profile 4botbsc --browser webkit

# Sync cookies
cp auth/4botbsc/storageState.json config/profiles/4botbsc/storageState.json

# Restart monitor
pkill -f monitor_mentions.py
nohup python monitor_mentions.py > Docs/status/mention_monitor.log 2>&1 &
```

### No Replies Being Posted
1. **Check if mentions exist:** Visit https://x.com/notifications/mentions
2. **Check reply history:** `cat replied_mentions.json` - verify tweet not already replied
3. **Test manual reply:** Edit `reply_to_mention.py` with specific tweet URL and run
4. **Check logs:** `tail -50 Docs/status/mention_monitor.log`
5. **Verify auth:** `python test_auth_correct_path.py`

### Clear Reply History (Reset)
```bash
# CAUTION: This will allow re-replying to all previous mentions
rm /Users/doctordre/projects/4bot/replied_mentions.json
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Memory Usage | ~34MB idle, ~350MB during reply |
| Check Duration | 8-12 seconds |
| Reply Duration | 15-20 seconds |
| Check Interval | 15 minutes (900s) |
| Reply Delay | 10 seconds between replies |
| Max Concurrency | 1 (sequential processing) |

## Safety Features

✅ **Duplicate Prevention**: replied_mentions.json tracking
✅ **Rate Limiting**: 15-minute check intervals
✅ **Human-like Timing**: Character-by-character typing (30ms delays)
✅ **Error Recovery**: Try-catch blocks with screenshot diagnostics
✅ **Resource Cleanup**: Browser closes after each operation
✅ **Graceful Degradation**: Continues after individual failures

## Integration Points

- **X.com Mentions API**: `https://x.com/notifications/mentions`
- **Tweet Status URLs**: `https://x.com/{user}/status/{id}`
- **Reply Button**: `[data-testid="reply"]`
- **Text Area**: `[data-testid="tweetTextarea_0"]`
- **Submit Shortcut**: `Control+Enter`

## Success Indicators

✅ **Monitor Running**: `ps aux | grep monitor_mentions.py` shows process
✅ **Reply History Growing**: `wc -l replied_mentions.json` increases over time
✅ **Log Output**: `mention_monitor.log` shows periodic checks
✅ **Authentication Valid**: `test_auth_correct_path.py` detects profile link
✅ **No Errors**: Log file shows "✅ No new mentions" or "✅ Replied with..."

## Emergency Procedures

### Complete System Reset
```bash
# Stop all monitors
pkill -f monitor_mentions.py

# Clear reply history (optional)
rm /Users/doctordre/projects/4bot/replied_mentions.json

# Re-authenticate
cd /Users/doctordre/projects/4bot
xbot login --profile 4botbsc --browser webkit

# Sync cookies
cp auth/4botbsc/storageState.json config/profiles/4botbsc/storageState.json

# Verify auth
python test_auth_correct_path.py

# Restart monitor
nohup python monitor_mentions.py > Docs/status/mention_monitor.log 2>&1 &

# Verify running
ps aux | grep monitor_mentions.py | grep -v grep
```

### Check for Hanging Processes
```bash
# Find all Python processes
ps aux | grep python | grep 4bot

# Kill specific PID if needed
kill -9 [PID]

# Clean restart
pkill -f monitor_mentions.py
sleep 2
nohup python monitor_mentions.py > Docs/status/mention_monitor.log 2>&1 &
```

## Monitoring Dashboard (One-Liner)
```bash
# Quick status summary
echo "=== @4botbsc Mention Monitor Status ===" && \
ps aux | grep monitor_mentions.py | grep -v grep | awk '{print "✅ Running - PID: "$2", Memory: "$6}' || echo "❌ Not running" && \
echo -n "Replied Tweets: " && (cat /Users/doctordre/projects/4bot/replied_mentions.json 2>/dev/null | jq length || echo "0") && \
echo -n "Auth Valid: " && (python /Users/doctordre/projects/4bot/test_auth_correct_path.py 2>&1 | grep -q "AUTHENTICATED" && echo "✅ Yes" || echo "❌ No") && \
echo -n "Last Check: " && (tail -1 /Users/doctordre/projects/4bot/Docs/status/mention_monitor.log 2>/dev/null | grep "Checking mentions" | awk '{print $4, $5}' || echo "Unknown")
```

## Maintenance Schedule

### Daily
- ✅ Verify monitor process running: `ps aux | grep monitor_mentions.py`
- ✅ Check log for errors: `tail -20 mention_monitor.log`

### Weekly
- ✅ Verify auth still valid: `python test_auth_correct_path.py`
- ✅ Review replied_mentions.json growth

### Monthly
- ✅ Re-authenticate via xbot CLI (cookie refresh)
- ✅ Sync cookies to both locations
- ✅ Restart monitor for clean slate

---
*Quick Reference Card - Generated: 2025-10-17 02:17 UTC*
*For full documentation, see: mention_monitoring_deployment.md*
