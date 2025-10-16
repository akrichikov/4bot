# RabbitMQ Integration for 4bot

## Overview
This document describes the RabbitMQ messaging infrastructure for the 4bot X/Twitter automation system.

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│ Twitter         │         │  RabbitMQ Exchange   │         │ Consumer/       │
│ Notification    │────────►│ 4botbsc_exchange     │────────►│ Command         │
│ Parser          │         │ (Topic Exchange)     │         │ Processor       │
└─────────────────┘         └──────────────────────┘         └─────────────────┘
                                     │
                           ┌─────────┴─────────┐
                           │                   │
                    ┌──────▼──────┐     ┌─────▼──────┐
                    │ 4bot_request│     │4bot_response│
                    │    Queue    │     │   Queue    │
                    └─────────────┘     └────────────┘
```

## Configuration

### Exchange
- **Name**: `4botbsc_exchange`
- **Type**: Topic Exchange
- **Durable**: Yes
- **Auto-delete**: No

### Queues
1. **4bot_request**
   - Purpose: Incoming commands and requests
   - Routing Key: `4bot.request.*`
   - Examples: `4bot.request.command`, `4bot.request.action`

2. **4bot_response**
   - Purpose: Outgoing notifications and responses
   - Routing Key: `4bot.response.*`
   - Examples: `4bot.response.notification`, `4bot.response.status`

## Environment Variables (.env)

```bash
# RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672/%2f
RABBITMQ_HOST=127.0.0.1
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# 4bot Exchange and Queues
RABBITMQ_EXCHANGE=4botbsc_exchange
RABBITMQ_EXCHANGE_TYPE=topic
RABBITMQ_REQUEST_QUEUE=4bot_request
RABBITMQ_RESPONSE_QUEUE=4bot_response
RABBITMQ_REQUEST_ROUTING_KEY=4bot.request.*
RABBITMQ_RESPONSE_ROUTING_KEY=4bot.response.*

# RabbitMQ Settings
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_DURABLE=true
RABBITMQ_AUTO_DELETE=false
RABBITMQ_AUTO_ACK=false
```

## Setup

### Initial Setup
```bash
# Install dependencies
pip install pika

# Run setup script to create exchange and queues
python rabbitmq_setup.py
```

### Verify Setup
```bash
# Check queues
rabbitmqctl list_queues name messages consumers | grep 4bot

# Check exchange
rabbitmqctl list_exchanges | grep 4botbsc
```

## Usage

### Publishing Notifications
```python
from rabbitmq_manager import NotificationPublisher

publisher = NotificationPublisher()

# Publish different notification types
publisher.publish_follow("elonmusk", {"verified": True})
publisher.publish_like("tim_cook", "post_12345")
publisher.publish_mention("sundarpichai", "Great work!", "post_67890")
publisher.publish_reply("satyanadella", "Thanks!", "post_11111")
publisher.publish_retweet("jeffbezos", "post_22222")

publisher.close()
```

### Consuming Commands
```python
from rabbitmq_manager import CommandConsumer

consumer = CommandConsumer()
consumer.start()  # Starts listening for commands
```

### Twitter → RabbitMQ Bridge
```python
# Run the bridge to capture Twitter notifications and publish to RabbitMQ
python notification_rabbitmq_bridge.py 60  # Monitor for 60 seconds
```

## Message Format

### BotMessage Structure
```json
{
  "message_id": "notif_1234567890",
  "message_type": "notification|command|response|error",
  "timestamp": "2025-10-16T20:00:00Z",
  "source": "twitter|system|user",
  "data": {
    // Message-specific data
  },
  "metadata": {
    // Optional metadata
  }
}
```

### Notification Example
```json
{
  "message_id": "notif_1760613150",
  "message_type": "notification",
  "timestamp": "2025-10-16T20:00:00Z",
  "source": "twitter",
  "data": {
    "type": "follow",
    "from_user": "elonmusk",
    "user_info": {
      "display_name": "Elon Musk",
      "verified": true
    }
  }
}
```

### Command Example
```json
{
  "message_id": "cmd_1760613150",
  "message_type": "command",
  "timestamp": "2025-10-16T20:00:00Z",
  "source": "user",
  "data": {
    "command": "post_tweet",
    "parameters": {
      "content": "Hello from 4bot!",
      "media": []
    }
  }
}
```

## Testing

### Test Publisher
```bash
# Send test messages
python test_rabbitmq_consumer.py publish
```

### Test Consumer
```bash
# Listen for messages
python test_rabbitmq_consumer.py
```

### End-to-End Test
1. Start consumer in one terminal: `python test_rabbitmq_consumer.py`
2. Send test messages in another: `python test_rabbitmq_consumer.py publish`
3. Verify messages are received and processed

## Files

- `rabbitmq_setup.py` - Creates exchange and queues
- `rabbitmq_manager.py` - Core RabbitMQ management classes
- `notification_rabbitmq_bridge.py` - Bridges Twitter notifications to RabbitMQ
- `test_rabbitmq_consumer.py` - Test consumer and publisher
- `.env` - Environment configuration

## Management Commands

```bash
# List all queues
rabbitmqctl list_queues

# List bindings
rabbitmqctl list_bindings

# Purge a queue
rabbitmqctl purge_queue 4bot_request

# Delete a queue (careful!)
rabbitmqctl delete_queue 4bot_request

# Monitor in real-time
rabbitmq-diagnostics observer
```

## RabbitMQ Management UI

Access the web interface at: http://localhost:15672
- Username: guest
- Password: guest

## Troubleshooting

### Connection Issues
- Ensure RabbitMQ is running: `brew services list | grep rabbitmq`
- Start RabbitMQ: `brew services start rabbitmq`
- Check logs: `tail -f /opt/homebrew/var/log/rabbitmq/*.log`

### Message Processing Errors
- Check consumer logs for error details
- Verify message format matches BotMessage structure
- Ensure handlers are registered for message types

### Queue Buildup
- Check consumer count: `rabbitmqctl list_queues name messages consumers`
- Increase prefetch count if needed
- Scale consumers horizontally for high load

## Integration with hYperStorm-App

The hYperStorm-App project at `/Users/doctordre/projects/hYperStorm-App/` also uses RabbitMQ with the same connection settings. The 4bot system can potentially integrate with hYperStorm's agent system through shared RabbitMQ infrastructure.

## Next Steps

1. Implement actual Twitter API actions in command handlers
2. Add message persistence and retry logic
3. Implement dead letter queues for failed messages
4. Add monitoring and alerting
5. Scale consumers based on load
6. Integrate with hYperStorm agent system