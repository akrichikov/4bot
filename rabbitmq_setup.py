#!/usr/bin/env python3
"""
RabbitMQ Setup for 4bot
Creates exchange and queues for X/Twitter bot messaging
"""

import pika
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class RabbitMQSetup:
    """Setup RabbitMQ exchange and queues for 4bot"""

    def __init__(self):
        self.host = os.getenv('RABBITMQ_HOST', '127.0.0.1')
        self.port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.user = os.getenv('RABBITMQ_USER', 'guest')
        self.password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        self.vhost = os.getenv('RABBITMQ_VHOST', '/')

        self.exchange = os.getenv('RABBITMQ_EXCHANGE', '4botbsc_exchange')
        self.exchange_type = os.getenv('RABBITMQ_EXCHANGE_TYPE', 'topic')
        self.request_queue = os.getenv('RABBITMQ_REQUEST_QUEUE', '4bot_request')
        self.response_queue = os.getenv('RABBITMQ_RESPONSE_QUEUE', '4bot_response')
        self.request_routing_key = os.getenv('RABBITMQ_REQUEST_ROUTING_KEY', '4bot.request.*')
        self.response_routing_key = os.getenv('RABBITMQ_RESPONSE_ROUTING_KEY', '4bot.response.*')

        self.durable = os.getenv('RABBITMQ_DURABLE', 'true').lower() == 'true'
        self.auto_delete = os.getenv('RABBITMQ_AUTO_DELETE', 'false').lower() == 'true'

        self.connection = None
        self.channel = None

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

            logger.info(f"✅ Connected to RabbitMQ at {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False

    def setup_exchange(self) -> bool:
        """Create the exchange"""
        try:
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type=self.exchange_type,
                durable=self.durable,
                auto_delete=self.auto_delete
            )
            logger.info(f"✅ Created exchange: {self.exchange} (type: {self.exchange_type})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create exchange: {e}")
            return False

    def setup_queues(self) -> bool:
        """Create the request and response queues"""
        try:
            # Create request queue
            self.channel.queue_declare(
                queue=self.request_queue,
                durable=self.durable,
                auto_delete=self.auto_delete
            )
            logger.info(f"✅ Created queue: {self.request_queue}")

            # Create response queue
            self.channel.queue_declare(
                queue=self.response_queue,
                durable=self.durable,
                auto_delete=self.auto_delete
            )
            logger.info(f"✅ Created queue: {self.response_queue}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create queues: {e}")
            return False

    def setup_bindings(self) -> bool:
        """Bind queues to exchange with routing keys"""
        try:
            # Bind request queue
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=self.request_queue,
                routing_key=self.request_routing_key
            )
            logger.info(f"✅ Bound {self.request_queue} to {self.exchange} with key: {self.request_routing_key}")

            # Bind response queue
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=self.response_queue,
                routing_key=self.response_routing_key
            )
            logger.info(f"✅ Bound {self.response_queue} to {self.exchange} with key: {self.response_routing_key}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create bindings: {e}")
            return False

    def verify_setup(self) -> Dict[str, Any]:
        """Verify the setup by getting queue info"""
        try:
            request_info = self.channel.queue_declare(queue=self.request_queue, passive=True)
            response_info = self.channel.queue_declare(queue=self.response_queue, passive=True)

            info = {
                "exchange": self.exchange,
                "exchange_type": self.exchange_type,
                "request_queue": {
                    "name": self.request_queue,
                    "message_count": request_info.method.message_count,
                    "consumer_count": request_info.method.consumer_count
                },
                "response_queue": {
                    "name": self.response_queue,
                    "message_count": response_info.method.message_count,
                    "consumer_count": response_info.method.consumer_count
                },
                "bindings": {
                    "request": self.request_routing_key,
                    "response": self.response_routing_key
                }
            }

            return info

        except Exception as e:
            logger.error(f"❌ Failed to verify setup: {e}")
            return {}

    def send_test_message(self) -> bool:
        """Send a test message to verify the setup"""
        try:
            test_message = {
                "type": "test",
                "message": "4bot RabbitMQ setup verification",
                "timestamp": "2025-10-16T19:30:00Z"
            }

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key='4bot.request.test',
                body=json.dumps(test_message),
                properties=pika.BasicProperties(
                    delivery_mode=2 if self.durable else 1
                )
            )

            logger.info("✅ Test message sent successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send test message: {e}")
            return False

    def cleanup(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("🔌 Connection closed")

    def full_setup(self) -> bool:
        """Run the complete setup process"""
        logger.info("=" * 70)
        logger.info("🚀 Starting RabbitMQ setup for 4bot")
        logger.info("=" * 70)

        if not self.connect():
            return False

        if not self.setup_exchange():
            return False

        if not self.setup_queues():
            return False

        if not self.setup_bindings():
            return False

        # Verify the setup
        info = self.verify_setup()
        if info:
            logger.info("\n📊 Setup Verification:")
            logger.info(json.dumps(info, indent=2))

        # Send test message
        self.send_test_message()

        logger.info("\n" + "=" * 70)
        logger.info("✨ RabbitMQ setup completed successfully!")
        logger.info("=" * 70)

        return True


def main():
    """Main execution"""
    setup = RabbitMQSetup()

    try:
        success = setup.full_setup()
        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted by user")

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

    finally:
        setup.cleanup()


if __name__ == "__main__":
    main()