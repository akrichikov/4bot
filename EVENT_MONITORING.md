# X/Twitter Event Monitoring System

## Overview

This system provides real-time monitoring and interception of X/Twitter posts directly from the browser using DOM observation. It supports pattern-based subscriptions, multiple notification channels, and flexible filtering.

## Architecture

### Core Components

1. **Event Interceptor** (`xbot/event_interceptor.py`)
   - Injects JavaScript MutationObserver into the page
   - Monitors DOM changes for new posts (article elements)
   - Extracts post data (content, author, metrics, media)
   - Sends events back to Python via console messages

2. **Notification System** (`xbot/notifications.py`)
   - Multiple notification channels:
     - Console output with formatted post details
     - Desktop notifications (macOS via osascript)
     - Webhook support for external integrations
     - JSONL logging for persistence
   - Notification aggregation for batch processing
   - Advanced filtering based on metrics

3. **Pattern Subscriptions**
   - Keyword-based filtering
   - Author-based monitoring
   - Regex pattern matching
   - Combinable filters with exclusions

## Quick Start

### 1. Basic Monitoring

```bash
# Monitor specific keywords
python quick_monitor.py keywords AI blockchain crypto

# Monitor specific author
python quick_monitor.py author elonmusk

# Monitor trending posts (min 500 engagements)
python quick_monitor.py trending 500

# Collect sample posts
python quick_monitor.py sample 20
```

### 2. Full Test Implementation

```bash
# Run with instant notifications
python test_event_monitor.py

# Run with batch notifications (60s intervals)
python test_event_monitor.py batch
```

### 3. Custom Configuration

Edit `monitor_config.json` to customize:
- Subscription patterns (keywords, authors, regex)
- Notification settings (desktop, webhook, logging)
- Filter thresholds (min likes, retweets, etc.)
- Browser settings (headless mode, scroll behavior)

## Event Flow

```
Browser Page
     ↓
DOM MutationObserver (JavaScript)
     ↓
Extract Post Data
     ↓
Console Message: __POST_EVENT__:{json}
     ↓
Python Event Interceptor
     ↓
Pattern Matching & Subscriptions
     ↓
Notification Handlers
     ↓
[Desktop | Console | Webhook | Log]
```

## Post Event Data Structure

```python
@dataclass
class PostEvent:
    id: str                    # Unique post ID
    author: str                # Display name
    author_handle: str         # Username without @
    content: str              # Full text content
    timestamp: datetime       # When intercepted
    likes: int               # Like count
    retweets: int           # Retweet count
    replies: int            # Reply count
    has_media: bool         # Contains media
    media_urls: List[str]   # Media URLs
    is_retweet: bool       # Is a retweet
    is_reply: bool         # Is a reply
```

## Pattern Subscription Examples

### Keyword Subscription
```python
subscription = create_keyword_subscription(
    name="Crypto Monitor",
    keywords=["bitcoin", "ethereum", "crypto"],
    callback=handle_crypto_post
)
interceptor.add_subscription(subscription)
```

### Author Subscription
```python
subscription = create_author_subscription(
    name="Tech Leaders",
    authors=["elonmusk", "sama", "karpathy"],
    callback=handle_tech_leader_post
)
interceptor.add_subscription(subscription)
```

### Regex Pattern Subscription
```python
subscription = create_regex_subscription(
    name="Stock Tickers",
    patterns=[r"\$[A-Z]{2,5}", r"NYSE:[A-Z]+"],
    callback=handle_stock_mention
)
interceptor.add_subscription(subscription)
```

### Advanced Subscription with Exclusions
```python
subscription = PatternSubscription(
    id="filtered_tech",
    name="Tech without spam",
    keywords={"AI", "machine learning"},
    exclude_keywords={"giveaway", "follow", "retweet"},
    exclude_patterns=[re.compile(r"win \$\d+")],
    callback=handle_filtered_tech
)
```

## Notification Configuration

### Desktop Notifications (macOS)
```python
notification_config = {
    'desktop_notifications': True,
    'console_output': True
}
```

### Webhook Integration
```python
notification_config = {
    'webhook_url': 'https://your-webhook.com/endpoint',
    'log_file': 'notifications.jsonl'
}
```

### Batch Processing
```python
aggregator = NotificationAggregator(
    handler=notification_handler,
    interval_seconds=60  # Batch every minute
)
await aggregator.start()
```

## Advanced Filtering

```python
filter = NotificationFilter()
filter.min_likes = 100          # Minimum likes
filter.min_retweets = 50        # Minimum retweets
filter.require_media = True     # Must have media
filter.exclude_retweets = True  # Skip retweets
filter.verified_only = True     # Only verified accounts
```

## Browser Setup

The system uses Playwright with:
- Chrome cookies from Profile 13 (4botbsc@gmail.com)
- Anti-automation detection measures
- Automatic scrolling to load new posts
- Configurable headless/headful mode

## Logging

All events are logged to:
- Console output (formatted)
- `event_monitor.log` (application logs)
- `notifications.jsonl` (post data in JSONL format)

## Troubleshooting

### No Posts Detected
- Ensure cookies are valid and up-to-date
- Check if logged into correct account
- Verify article selector matches current X/Twitter HTML

### Notifications Not Showing
- macOS: Grant terminal notification permissions
- Check osascript is available
- Verify notification settings in config

### High Memory Usage
- Reduce buffer_size in configuration
- Enable headless mode
- Implement post count limits

## Security Notes

- Cookies are stored locally in `auth_data/x_cookies.json`
- No credentials are transmitted to external services
- Webhook URLs should use HTTPS
- Monitor logs for sensitive information before sharing

## Performance Considerations

- DOM observation is lightweight but continuous
- Scrolling interval affects new post discovery rate
- Batch processing reduces notification overhead
- Pattern matching complexity affects CPU usage

## Future Enhancements

- [ ] Support for Twitter Spaces monitoring
- [ ] Multi-account monitoring
- [ ] Sentiment analysis on posts
- [ ] Database storage for historical analysis
- [ ] Web dashboard for real-time monitoring
- [ ] Mobile push notifications
- [ ] Advanced analytics and reporting