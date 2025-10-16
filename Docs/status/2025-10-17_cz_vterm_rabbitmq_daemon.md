# CZ VTerm RabbitMQ Daemon - Complete Implementation

**Date:** 2025-10-17
**Status:** READY FOR DEPLOYMENT ✅
**Pipeline:** Notifications → VTerm → RabbitMQ → Reply Posting

## Executive Summary

Successfully implemented a complete notification-to-reply pipeline that:
1. **Monitors @4botbsc mentions** in headless mode
2. **Filters notifications** to only process direct mentions
3. **Sends to VTerm HTTP queue** for CZ reply generation
4. **Publishes to RabbitMQ** persistent queues
5. **Posts replies** using tab-managed browser instances
6. **Runs as launchd daemon** for continuous operation

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           X/Twitter Notifications               │
│         (Headless Browser Monitor)              │
└─────────────────┬───────────────────────────────┘
                  │ @4botbsc mentions only
                  ▼
┌─────────────────────────────────────────────────┐
│          NotificationMonitor                     │
│   • Filters for @4botbsc mentions               │
│   • Extracts: author, content, URL              │
│   • Tab management for isolated operations      │
└─────────────────┬───────────────────────────────┘
                  │ NotificationEvent
                  ▼
┌─────────────────────────────────────────────────┐
│         VTerm HTTP Queue (Port 8765)            │
│   • /queue/run endpoint                         │
│   • Python script for CZ reply generation       │
│   • Returns job_id for async processing         │
└─────────────────┬───────────────────────────────┘
                  │ Generated Reply
                  ▼
┌─────────────────────────────────────────────────┐
│      RabbitMQ (Persistent Queues)               │
│   • Exchange: 4botbsc_exchange                  │
│   • Request Queue: 4bot_request (durable)       │
│   • Response Queue: 4bot_response (durable)     │
│   • Topic routing: 4bot.request.reply           │
└─────────────────┬───────────────────────────────┘
                  │ Reply Message
                  ▼
┌─────────────────────────────────────────────────┐
│          Reply Poster (Consumer)                │
│   • Consumes from RabbitMQ                      │
│   • Creates authenticated browser tab           │
│   • Posts reply to X/Twitter                    │
│   • Auto-closes tab after posting               │
└─────────────────────────────────────────────────┘
```

## Key Components

### 1. **cz_vterm_rabbitmq_daemon.py** (Main Daemon)
- Complete pipeline orchestrator
- Integrates all components
- Tab management for browser isolation
- Async/await architecture

### 2. **TabManager Class**
- Creates isolated browser contexts
- Auto-cleanup after each operation
- Cookie-based authentication
- Memory efficient (no persistent sessions)

### 3. **VTermHTTPClient**
- Communicates with VTerm HTTP server
- Queues CZ reply generation jobs
- Polls for job completion
- Returns structured JSON results

### 4. **NotificationMonitor**
- Headless browser automation
- Filters @4botbsc mentions only
- Prevents self-reply loops
- Tracks processed notification IDs

### 5. **RabbitMQBridge**
- Publishes replies to persistent queues
- Consumes reply requests
- Posts to Twitter via authenticated tabs
- Handles success/failure responses

## Configuration

### Environment Variables (.env)
```bash
X_USER=4botbsc@gmail.com
X_PASSWD=RLLYhEqEPM@gJ3vY

# RabbitMQ Configuration (Verified Durable)
RABBITMQ_HOST=127.0.0.1
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# 4bot Exchange and Queues (Persistent)
RABBITMQ_EXCHANGE=4botbsc_exchange
RABBITMQ_EXCHANGE_TYPE=topic
RABBITMQ_REQUEST_QUEUE=4bot_request     # durable=true ✅
RABBITMQ_RESPONSE_QUEUE=4bot_response   # durable=true ✅
RABBITMQ_REQUEST_ROUTING_KEY=4bot.request.*
RABBITMQ_RESPONSE_ROUTING_KEY=4bot.response.*

# Settings
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_DURABLE=true
RABBITMQ_AUTO_DELETE=false
RABBITMQ_AUTO_ACK=false
```

### Authentication Files
- **Cookies:** `/Users/doctordre/projects/4bot/auth_data/x_cookies.json`
- **Storage State:** `/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json`
- **User Data:** `.x-user/4botbsc/`

## Deployment Instructions

### Prerequisites
```bash
# Ensure RabbitMQ is running
brew services start rabbitmq

# Start VTerm HTTP server
python3 -m xbot.vterm_http &

# Verify queues are durable
rabbitmqctl list_queues name durable | grep 4bot
```

### Launch Options

#### 1. Foreground Mode (Testing)
```bash
./launch_cz_daemon.sh
```

#### 2. LaunchD Daemon (Production)
```bash
# Install and start as daemon
./launch_cz_daemon.sh launchd

# Check status
./launch_cz_daemon.sh status

# Stop daemon
./launch_cz_daemon.sh stop
```

#### 3. Manual LaunchD Control
```bash
# Install
cp com.4botbsc.cz-daemon.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist
rm ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist

# View logs
tail -f logs/cz_daemon.out.log
tail -f logs/cz_daemon.err.log
```

## CZ Reply Generation Logic

The daemon generates contextual CZ replies based on content:

```python
# FUD/Negativity → "4"
if 'scam' or 'rug' or 'crash' in content:
    return "4"

# Building/Positive → Encouragement
if 'build' or 'develop' in content:
    return "This is the way! Keep BUIDLing 🚀"

# Questions → Wisdom
if '?' in content:
    if 'when': return "The best time was yesterday..."
    if 'how': return "Start small, learn constantly..."

# Mentions → Support
return "Appreciate you! Let's keep building..."
```

## Monitoring & Logs

### Process Status
```bash
# Check all components
./launch_cz_daemon.sh status

# View RabbitMQ queues
rabbitmqctl list_queues name messages

# Check VTerm health
curl http://127.0.0.1:8765/health

# Monitor daemon logs
tail -f logs/cz_daemon.out.log
```

### Key Metrics
- **Notification Check Interval:** 30 seconds
- **VTerm Job Timeout:** 30 seconds
- **Tab Cleanup:** Immediate after each operation
- **RabbitMQ Prefetch:** 10 messages
- **Rate Limiting:** Built into tab creation

## Features Implemented

✅ **Headless Browser Operations** - All browser instances run headless
✅ **@4botbsc Mention Filtering** - Only processes direct mentions
✅ **Self-Post Prevention** - Filters out 4botbsc's own posts
✅ **VTerm HTTP Integration** - Uses queue endpoints for async processing
✅ **Persistent RabbitMQ Queues** - Survives restarts (durable=true)
✅ **Tab Management** - Auto-cleanup prevents memory leaks
✅ **Cookie Authentication** - Uses stored cookies for login
✅ **LaunchD Daemon** - Runs continuously as background service
✅ **Error Recovery** - KeepAlive ensures daemon restarts on crash
✅ **Comprehensive Logging** - Separate stdout/stderr logs

## Security Considerations

1. **Authentication:** Uses cookies/storage state (no passwords in memory)
2. **Network:** All services run on localhost (127.0.0.1)
3. **Permissions:** Daemon runs as user (not root)
4. **Rate Limiting:** Natural delays from tab creation
5. **Resource Management:** Tabs auto-close after use

## Troubleshooting

### Daemon Won't Start
```bash
# Check prerequisites
rabbitmqctl status
curl http://127.0.0.1:8765/health

# View error logs
tail -f logs/cz_daemon.err.log
```

### Not Posting Replies
```bash
# Check RabbitMQ messages
rabbitmqctl list_queues name messages

# Verify authentication
ls -la auth_data/x_cookies.json
ls -la config/profiles/4botbsc/storageState.json
```

### Memory Issues
```bash
# The tab manager auto-closes tabs
# But if needed, restart daemon:
./launch_cz_daemon.sh stop
./launch_cz_daemon.sh launchd
```

## Files Created

1. **`cz_vterm_rabbitmq_daemon.py`** - Main daemon with complete pipeline
2. **`cz_notification_daemon.py`** - Alternative simpler implementation
3. **`com.4botbsc.cz-daemon.plist`** - LaunchD configuration
4. **`launch_cz_daemon.sh`** - Control script for daemon
5. **Updated `rabbitmq_manager.py`** - Added topology ensure for durability

## Conclusion

The CZ VTerm RabbitMQ Daemon is fully implemented and ready for deployment. It provides a robust, scalable pipeline for automatically responding to @4botbsc mentions with contextual CZ-persona replies. The system is designed for reliability with persistent queues, automatic recovery, and efficient resource management through tab isolation.

**Next Steps:**
1. Run `./launch_cz_daemon.sh launchd` to deploy
2. Monitor logs for first replies
3. Adjust notification check interval if needed
4. Consider adding more sophisticated CZ reply patterns