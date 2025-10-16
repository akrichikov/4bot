# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

4bot is an X/Twitter automation system built with Playwright for browser automation. It uses cookie-based authentication, real-time DOM manipulation for event capture, and RabbitMQ for async message processing.

## Core Architecture

### Authentication & Browser Control
- **Cookie-based auth**: Stored in `auth_data/x_cookies.json` and `chrome_profiles/cookies/`
- **Browser automation**: Playwright with Chrome/Chromium, headless or headed modes
- **Profile management**: Multiple Chrome profiles mapped to different X accounts (see `chrome_profiles/profile_mapper.py`)
- **Cookie format**: Must convert integer `secure`/`httpOnly` fields to booleans for Playwright compatibility

### Event Capture System
- **DOM MutationObserver**: JavaScript injection to monitor real-time DOM changes
- **Console message passing**: Pattern `__POST_EVENT__:`, `__NOTIFICATION__:`, `__NOTIFICATION_JSON__:` for JS→Python communication
- **Selectors**: Primary identifiers are `data-testid` attributes (e.g., `tweetText`, `cellInnerDiv`)

### Message Queue Architecture
- **RabbitMQ Exchange**: `4botbsc_exchange` (topic exchange)
- **Queues**: `4bot_request` (commands), `4bot_response` (notifications)
- **Routing patterns**: `4bot.request.*`, `4bot.response.*`
- **Message format**: BotMessage dataclass with `message_id`, `message_type`, `timestamp`, `source`, `data`

## Common Commands

```bash
# Setup & Dependencies
pip install -r requirements.txt --break-system-packages  # macOS system Python
pip install pika playwright python-dotenv pydantic typer rich

# Fix cookie format issues
python fix_cookies.py

# RabbitMQ Setup
python rabbitmq_setup.py  # Create exchange and queues
rabbitmqctl list_queues name messages consumers | grep 4bot  # Verify queues

# Monitoring & Parsing
python final_notification_json_parser.py 60  # Parse notifications for 60 seconds
python notification_rabbitmq_bridge.py 45  # Bridge notifications to RabbitMQ
python dual_monitor.py  # Monitor feed + notifications simultaneously

# Testing
python test_rabbitmq_consumer.py  # Start consumer
python test_rabbitmq_consumer.py publish  # Send test messages
pytest tests/ -v  # Run all tests
pytest tests/test_vterm_http.py::test_basic_request -v  # Run single test

# CLI (xbot module)
xbot cookies export auth_data/cookies.json  # Export cookies
xbot session check  # Check login status
xbot health selectors  # Test DOM selectors
```

## Key Files & Their Purposes

### Core Notification System
- `final_notification_json_parser.py` - Main notification parser with Unicode support
- `notification_rabbitmq_bridge.py` - Bridges Twitter notifications to RabbitMQ
- `rabbitmq_manager.py` - RabbitMQ publisher/consumer classes
- `dual_monitor.py` - Simultaneous feed and notification monitoring

### Browser Automation
- `xbot/facade.py` - Main XBot class for Twitter interactions
- `xbot/browser.py` - Browser lifecycle management
- `xbot/event_interceptor.py` - DOM event capture system
- `chrome_profiles/profile_mapper.py` - Chrome profile management

### Authentication
- `auth_data/x_cookies.json` - Primary cookie storage
- `chrome_profiles/cookies/` - Per-profile cookie files
- `.env` - Credentials (x_user, x_passwd) and RabbitMQ config

## Critical Implementation Details

### Unicode Handling
Use hash functions instead of btoa() for ID generation to avoid Latin1 range errors:
```javascript
function generateId(text) {
    let hash = 0;
    for (let i = 0; i < Math.min(text.length, 200); i++) {
        hash = ((hash << 5) - hash) + text.charCodeAt(i);
        hash = hash & hash;
    }
    return 'notif_' + Math.abs(hash).toString(36) + '_' + Date.now().toString(36);
}
```

### Cookie Format Conversion
Always convert integer secure/httpOnly to booleans:
```python
if isinstance(cookie.get('secure'), int):
    cookie['secure'] = bool(cookie['secure'])
```

### DOM Selector Priority
1. `data-testid` attributes (most reliable)
2. ARIA roles and labels
3. Class names (avoid - frequently change)

### Message Queue Patterns
- Use topic exchange for flexible routing
- Implement retry logic with exponential backoff
- Handle legacy message formats by mapping `type` → `message_type`

## Environment Variables

Required in `.env`:
```
x_user=4botbsc@gmail.com
x_passwd=<password>
RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672/%2f
RABBITMQ_EXCHANGE=4botbsc_exchange
RABBITMQ_REQUEST_QUEUE=4bot_request
RABBITMQ_RESPONSE_QUEUE=4bot_response
```

## Testing Strategy

1. **Cookie validation**: Always test with `browser_cookie_test.py` first
2. **Selector health**: Run `xbot health selectors` after X.com UI updates
3. **Message flow**: Use `test_rabbitmq_consumer.py` for end-to-end messaging
4. **Notification capture**: Test with `final_notification_json_parser.py` in short durations

## Common Issues & Solutions

### Navigation Timeouts
Use `wait_until='domcontentloaded'` instead of `'networkidle'`:
```python
await page.goto(url, wait_until='domcontentloaded', timeout=30000)
```

### Cookie Rejection
Fix format with `fix_cookies.py` or ensure boolean conversion in code.

### RabbitMQ Connection Issues
```bash
brew services list | grep rabbitmq  # Check service
brew services restart rabbitmq      # Restart if needed
rabbitmqctl status                  # Verify running
```

### Notification Capture Failures
1. Refresh page every 15-20 seconds to prevent staleness
2. Re-inject extraction script after each refresh
3. Use Set() to track processed notification IDs

## Integration Points

- **hYperStorm-App**: Shares RabbitMQ infrastructure at localhost:5672
- **Redis**: Available at port 63795 (Homebrew installation)
- **LiveKit/WebRTC**: Potential for real-time streaming integration