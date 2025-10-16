#!/usr/bin/env python3
"""
RabbitMQ Manager for 4bot
Handles message publishing and consumption for X/Twitter bot operations
"""

import pika
import json
import os
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import logging
from pathlib import Path

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BotMessage:
    """Standard message format for 4bot messaging"""
    message_id: str
    message_type: str  # notification, command, response, error
    timestamp: str
    source: str  # twitter, system, user
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class RabbitMQManager:
    """Manages RabbitMQ connections and messaging for 4bot"""

    def __init__(self):
        # Connection settings
        self.host = os.getenv('RABBITMQ_HOST', '127.0.0.1')
        self.port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.user = os.getenv('RABBITMQ_USER', 'guest')
        self.password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        self.vhost = os.getenv('RABBITMQ_VHOST', '/')

        # Exchange and queue settings
        self.exchange = os.getenv('RABBITMQ_EXCHANGE', '4botbsc_exchange')
        self.request_queue = os.getenv('RABBITMQ_REQUEST_QUEUE', '4bot_request')
        self.response_queue = os.getenv('RABBITMQ_RESPONSE_QUEUE', '4bot_response')
        self.durable = os.getenv('RABBITMQ_DURABLE', 'true').lower() == 'true'
        self.prefetch_count = int(os.getenv('RABBITMQ_PREFETCH_COUNT', '10'))
        self.auto_ack = os.getenv('RABBITMQ_AUTO_ACK', 'false').lower() == 'true'

        # Connection objects
        self.connection = None
        self.channel = None
        self.consumer_tag = None

        # Message handlers
        self.message_handlers = {}

    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=self.prefetch_count)

            logger.info(f"✅ Connected to RabbitMQ at {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False

    def publish_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Publish a notification from Twitter to RabbitMQ"""
        try:
            message = BotMessage(
                message_id=f"notif_{datetime.now().timestamp()}",
                message_type="notification",
                timestamp=datetime.now().isoformat(),
                source="twitter",
                data=notification_data
            )

            self.publish_message(
                message=message,
                routing_key='4bot.response.notification'
            )

            logger.info(f"📤 Published notification: {notification_data.get('type', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish notification: {e}")
            return False

    def publish_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Publish a command to the bot"""
        try:
            message = BotMessage(
                message_id=f"cmd_{datetime.now().timestamp()}",
                message_type="command",
                timestamp=datetime.now().isoformat(),
                source="user",
                data={
                    "command": command,
                    "parameters": params or {}
                }
            )

            self.publish_message(
                message=message,
                routing_key='4bot.request.command'
            )

            logger.info(f"📤 Published command: {command}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish command: {e}")
            return False

    def publish_message(self, message: BotMessage, routing_key: str) -> bool:
        """Publish a message to RabbitMQ"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(asdict(message)),
                properties=pika.BasicProperties(
                    delivery_mode=2 if self.durable else 1,
                    content_type='application/json'
                )
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            return False

    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler for a specific message type"""
        self.message_handlers[message_type] = handler
        logger.info(f"📝 Registered handler for message type: {message_type}")

    def _process_message(self, channel, method, properties, body):
        """Process incoming messages"""
        try:
            # Parse message
            message_data = json.loads(body)

            # Handle legacy message format (convert 'type' to 'message_type')
            if 'type' in message_data and 'message_type' not in message_data:
                message_data['message_type'] = message_data.pop('type')

            # Ensure required fields exist with defaults
            if 'message_id' not in message_data:
                message_data['message_id'] = f"msg_{datetime.now().timestamp()}"
            if 'message_type' not in message_data:
                message_data['message_type'] = 'unknown'
            if 'timestamp' not in message_data:
                message_data['timestamp'] = datetime.now().isoformat()
            if 'source' not in message_data:
                message_data['source'] = 'unknown'
            if 'data' not in message_data:
                # For legacy messages, move all non-standard fields to data
                data_fields = {}
                for key in list(message_data.keys()):
                    if key not in ['message_id', 'message_type', 'timestamp', 'source', 'metadata']:
                        data_fields[key] = message_data.pop(key)
                message_data['data'] = data_fields

            message = BotMessage(**message_data)

            logger.info(f"📥 Received {message.message_type} message from {message.source}")

            # Find and execute handler
            handler = self.message_handlers.get(message.message_type)
            if handler:
                handler(message)
            else:
                logger.warning(f"⚠️ No handler for message type: {message.message_type}")

            # Acknowledge message if not auto-ack
            if not self.auto_ack:
                channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            if not self.auto_ack:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def consume_requests(self):
        """Start consuming request messages"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()

            self.channel.basic_consume(
                queue=self.request_queue,
                on_message_callback=self._process_message,
                auto_ack=self.auto_ack
            )

            logger.info(f"👂 Started consuming from {self.request_queue}")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("⏹️ Stopping consumer...")
            self.stop_consuming()

        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")

    def consume_responses(self):
        """Start consuming response messages"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()

            self.channel.basic_consume(
                queue=self.response_queue,
                on_message_callback=self._process_message,
                auto_ack=self.auto_ack
            )

            logger.info(f"👂 Started consuming from {self.response_queue}")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("⏹️ Stopping consumer...")
            self.stop_consuming()

        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")

    def stop_consuming(self):
        """Stop consuming messages"""
        if self.channel:
            self.channel.stop_consuming()
            logger.info("🛑 Stopped consuming messages")

    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("🔌 Connection closed")


class NotificationPublisher:
    """Publishes Twitter notifications to RabbitMQ"""

    def __init__(self):
        self.manager = RabbitMQManager()
        self.manager.connect()

    def publish_like(self, from_user: str, post_id: str):
        """Publish a like notification"""
        self.manager.publish_notification({
            "type": "like",
            "from_user": from_user,
            "post_id": post_id,
            "timestamp": datetime.now().isoformat()
        })

    def publish_follow(self, from_user: str, user_info: Dict[str, Any] = None):
        """Publish a follow notification"""
        self.manager.publish_notification({
            "type": "follow",
            "from_user": from_user,
            "user_info": user_info or {},
            "timestamp": datetime.now().isoformat()
        })

    def publish_mention(self, from_user: str, content: str, post_id: str):
        """Publish a mention notification"""
        self.manager.publish_notification({
            "type": "mention",
            "from_user": from_user,
            "content": content,
            "post_id": post_id,
            "timestamp": datetime.now().isoformat()
        })

    def publish_reply(self, from_user: str, content: str, post_id: str):
        """Publish a reply notification"""
        self.manager.publish_notification({
            "type": "reply",
            "from_user": from_user,
            "content": content,
            "post_id": post_id,
            "timestamp": datetime.now().isoformat()
        })

    def publish_retweet(self, from_user: str, post_id: str):
        """Publish a retweet notification"""
        self.manager.publish_notification({
            "type": "retweet",
            "from_user": from_user,
            "post_id": post_id,
            "timestamp": datetime.now().isoformat()
        })

    def close(self):
        """Close the publisher"""
        self.manager.close()


class CommandConsumer:
    """Consumes commands from RabbitMQ and executes bot actions"""

    def __init__(self):
        self.manager = RabbitMQManager()
        self.manager.connect()

        # Register command handlers
        self.manager.register_handler("command", self._handle_command)

    def _handle_command(self, message: BotMessage):
        """Handle incoming commands"""
        command = message.data.get("command")
        params = message.data.get("parameters", {})

        logger.info(f"🤖 Executing command: {command}")

        # Command routing
        if command == "post_tweet":
            self._post_tweet(params)
        elif command == "follow_user":
            self._follow_user(params)
        elif command == "like_post":
            self._like_post(params)
        elif command == "start_monitoring":
            self._start_monitoring(params)
        elif command == "stop_monitoring":
            self._stop_monitoring(params)
        else:
            logger.warning(f"⚠️ Unknown command: {command}")

    def _post_tweet(self, params: Dict[str, Any]):
        """Handle post tweet command"""
        content = params.get("content")
        logger.info(f"📝 Would post tweet: {content}")
        # TODO: Implement actual tweet posting

    def _follow_user(self, params: Dict[str, Any]):
        """Handle follow user command"""
        user = params.get("user")
        logger.info(f"➕ Would follow user: {user}")
        # TODO: Implement actual user following

    def _like_post(self, params: Dict[str, Any]):
        """Handle like post command"""
        post_id = params.get("post_id")
        logger.info(f"❤️ Would like post: {post_id}")
        # TODO: Implement actual post liking

    def _start_monitoring(self, params: Dict[str, Any]):
        """Handle start monitoring command"""
        logger.info("🔍 Would start monitoring")
        # TODO: Implement monitoring start

    def _stop_monitoring(self, params: Dict[str, Any]):
        """Handle stop monitoring command"""
        logger.info("🛑 Would stop monitoring")
        # TODO: Implement monitoring stop

    def start(self):
        """Start consuming commands"""
        logger.info("🚀 Starting command consumer...")
        self.manager.consume_requests()

    def stop(self):
        """Stop consuming commands"""
        self.manager.stop_consuming()
        self.manager.close()


def example_usage():
    """Example usage of RabbitMQ manager"""
    # Create publisher
    publisher = NotificationPublisher()

    # Publish some notifications
    publisher.publish_follow("elonmusk", {"verified": True, "followers": 150000000})
    publisher.publish_like("tim_cook", "1234567890")
    publisher.publish_mention("sundarpichai", "Check out this AI model!", "9876543210")

    # Clean up
    publisher.close()

    logger.info("\n✨ Example notifications published!")


if __name__ == "__main__":
    example_usage()