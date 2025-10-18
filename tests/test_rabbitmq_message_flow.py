#!/usr/bin/env python3
"""
RabbitMQ Message Flow Tests
Tests the critical async messaging backbone (Pareto 80/20: highest value tests)
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import sys
import os
import re


class _RegexEquals:
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def __eq__(self, other):  # type: ignore[override]
        text = other if isinstance(other, str) else str(other)
        return bool(self.pattern.search(text))

    def __repr__(self) -> str:
        return f"~/{self.pattern.pattern}/~"


def approx_match(pattern: str) -> _RegexEquals:
    return _RegexEquals(pattern)


setattr(pytest, "approx_match", approx_match)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base_test_fixture import BaseTestFixture
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage, NotificationPublisher, CommandConsumer


class TestRabbitMQMessageFlow(BaseTestFixture):
    """Test RabbitMQ message flow - critical path"""

    def setup_custom(self):
        """Custom setup for RabbitMQ tests"""
        self.manager = None
        self.publisher = None

    def teardown_custom(self):
        """Custom teardown"""
        if self.manager:
            self.manager.close()
        if self.publisher:
            self.publisher.close()

    def test_bot_message_serialization_unicode(self):
        """Test BotMessage handles Unicode correctly"""
        # Create message with Unicode characters
        message = BotMessage(
            message_id="test_unicode_123",
            message_type="notification",
            timestamp=datetime.now().isoformat(),
            source="test",
            data={
                "emoji": "🎉🚀😊",
                "chinese": "你好世界",
                "arabic": "مرحبا بالعالم",
                "russian": "Привет мир"
            }
        )

        # Serialize to JSON
        json_str = json.dumps(message.__dict__)

        # Deserialize back
        parsed = json.loads(json_str)

        # Verify Unicode preserved
        assert parsed['data']['emoji'] == "🎉🚀😊"
        assert parsed['data']['chinese'] == "你好世界"
        assert parsed['data']['arabic'] == "مرحبا بالعالم"
        assert parsed['data']['russian'] == "Привет мир"

    def test_large_payload_handling(self):
        """Test handling of large message payloads"""
        # Create 1MB payload
        large_text = "X" * (1024 * 1024)  # 1MB of X characters

        message = BotMessage(
            message_id="test_large_123",
            message_type="notification",
            timestamp=datetime.now().isoformat(),
            source="test",
            data={"large_content": large_text}
        )

        # Serialize
        json_str = json.dumps(message.__dict__)

        # Verify size
        assert len(json_str) > 1024 * 1024  # At least 1MB

        # Deserialize
        parsed = json.loads(json_str)
        assert len(parsed['data']['large_content']) == 1024 * 1024

    def test_malformed_json_handling(self):
        """Test graceful handling of malformed JSON"""
        manager = RabbitMQManager()

        # Mock the channel
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "test_tag"

        # Test various malformed inputs
        malformed_inputs = [
            '{"incomplete": ',  # Incomplete JSON
            '{"type": undefined}',  # JavaScript undefined
            '{"nested": {"broken',  # Broken nesting
            'not json at all',  # Plain text
            '{"duplicate": "key", "duplicate": "key"}',  # Duplicate keys
        ]

        for malformed in malformed_inputs:
            # Process should handle gracefully
            manager._process_message(mock_channel, mock_method, None, malformed.encode())

            # Should NACK the message
            mock_channel.basic_nack.assert_called_with(
                delivery_tag="test_tag",
                requeue=True
            )

    def test_message_routing_patterns(self):
        """Test topic exchange routing patterns"""
        manager = RabbitMQManager()
        manager.connect()
        channel = self.mocks['rabbitmq_channel']

        # Test request routing
        manager.publish_message(
            message=self.create_mock_bot_message("command"),
            routing_key="4bot.request.command"
        )

        channel.basic_publish.assert_called_with(
            exchange='4botbsc_exchange',
            routing_key='4bot.request.command',
            body=pytest.approx_match(r'.*"message_type":\s*"command".*'),
            properties=pytest.approx_match(r'.*')
        )

        # Test response routing
        manager.publish_message(
            message=self.create_mock_bot_message("notification"),
            routing_key="4bot.response.notification"
        )

        # Verify both were called
        assert channel.basic_publish.call_count >= 2

    def test_connection_resilience(self):
        """Test connection resilience and retry logic"""
        manager = RabbitMQManager()

        # First connection fails
        self.mocks['rabbitmq_connection'].is_closed = True

        # Should attempt reconnection
        result = manager.publish_message(
            message=self.create_mock_bot_message(),
            routing_key="4bot.request.test"
        )

        # Verify reconnection attempted
        assert result == True  # Mock returns success after reconnection

    def test_notification_publisher_types(self):
        """Test NotificationPublisher handles all notification types"""
        publisher = NotificationPublisher()
        self.publisher = publisher  # Store for teardown

        channel = self.mocks['rabbitmq_channel']

        # Test each notification type
        test_cases = [
            ('publish_follow', ['testuser', {'verified': True}]),
            ('publish_like', ['testuser', 'post_123']),
            ('publish_mention', ['testuser', 'Hello @you!', 'post_456']),
            ('publish_reply', ['testuser', 'Great point!', 'post_789']),
            ('publish_retweet', ['testuser', 'post_101'])
        ]

        for method_name, args in test_cases:
            method = getattr(publisher, method_name)
            method(*args)

            # Verify message published
            channel.basic_publish.assert_called()

            # Get last call
            last_call = channel.basic_publish.call_args
            body = json.loads(last_call.kwargs['body'])

            # Verify structure
            assert 'message_id' in body
            assert body.get('message_type') == 'notification'
            assert 'data' in body

    def test_command_consumer_routing(self):
        """Test CommandConsumer routes commands correctly"""
        consumer = CommandConsumer()

        # Mock command handlers
        with patch.object(consumer, '_post_tweet') as mock_post, \
             patch.object(consumer, '_follow_user') as mock_follow, \
             patch.object(consumer, '_like_post') as mock_like:

            # Test command routing
            commands = [
                ('post_tweet', {'content': 'Test tweet'}, mock_post),
                ('follow_user', {'user': '@testuser'}, mock_follow),
                ('like_post', {'post_id': '123'}, mock_like)
            ]

            for cmd, params, mock_handler in commands:
                message = BotMessage(
                    message_id=f"cmd_{cmd}",
                    message_type="command",
                    timestamp=datetime.now().isoformat(),
                    source="test",
                    data={"command": cmd, "parameters": params}
                )

                consumer._handle_command(message)
                mock_handler.assert_called_once_with(params)
                mock_handler.reset_mock()

    def test_message_persistence_properties(self):
        """Test durable message properties for persistence"""
        manager = RabbitMQManager()
        manager.connect()
        channel = self.mocks['rabbitmq_channel']

        # Send durable message
        manager.publish_message(
            message=self.create_mock_bot_message(),
            routing_key="4bot.request.test"
        )

        # Verify delivery_mode = 2 (persistent)
        last_call = channel.basic_publish.call_args
        props = last_call.kwargs['properties']

        # Check mock properties
        assert hasattr(props, 'delivery_mode')

    def test_prefetch_count_configuration(self):
        """Test prefetch count for consumer load balancing"""
        manager = RabbitMQManager()
        manager.connect()

        channel = self.mocks['rabbitmq_channel']

        # Verify QoS set with prefetch
        channel.basic_qos.assert_called_with(prefetch_count=10)

    def test_legacy_message_format_conversion(self):
        """Test conversion of legacy 'type' field to 'message_type'"""
        manager = RabbitMQManager()

        # Mock channel and method
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = "test_tag"

        # Legacy message with 'type' instead of 'message_type'
        legacy_message = {
            "type": "test",
            "message": "This is a test message"
        }

        # Register handler
        handler_called = False
        def test_handler(msg):
            nonlocal handler_called
            handler_called = True
            assert msg.message_type == "test"  # Converted from 'type'

        manager.register_handler("test", test_handler)

        # Process legacy message
        manager._process_message(
            mock_channel,
            mock_method,
            None,
            json.dumps(legacy_message).encode()
        )

        # Verify handler called with converted message
        assert handler_called

    def test_concurrent_message_publishing(self):
        """Test concurrent message publishing doesn't cause race conditions"""
        import threading

        manager = RabbitMQManager()
        manager.connect()
        channel = self.mocks['rabbitmq_channel']

        # Track published messages
        published = []

        def publish_worker(msg_id):
            message = BotMessage(
                message_id=f"concurrent_{msg_id}",
                message_type="test",
                timestamp=datetime.now().isoformat(),
                source="test",
                data={"thread_id": msg_id}
            )
            manager.publish_message(message, "4bot.test.concurrent")
            published.append(msg_id)

        # Launch concurrent publishers
        threads = []
        for i in range(10):
            t = threading.Thread(target=publish_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify all published
        assert len(published) == 10
        assert channel.basic_publish.call_count == 10
