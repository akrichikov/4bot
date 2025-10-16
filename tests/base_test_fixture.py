#!/usr/bin/env python3
"""
Base Test Fixture for 4bot
Provides reusable test infrastructure following DRY principles
"""

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import pytest
from dataclasses import dataclass, asdict
from datetime import datetime
import pika


class BaseTestFixture(ABC):
    """Abstract base class for all 4bot tests"""

    def setup_method(self):
        """Setup before each test method"""
        self.mocks = {}
        self.patches = []
        self._setup_rabbitmq_mocks()
        self._setup_browser_mocks()
        self._setup_cookie_mocks()
        self.setup_custom()

    def teardown_method(self):
        """Cleanup after each test method"""
        for p in self.patches:
            p.stop()
        self.teardown_custom()

    @abstractmethod
    def setup_custom(self):
        """Override in subclasses for specific setup"""
        pass

    @abstractmethod
    def teardown_custom(self):
        """Override in subclasses for specific teardown"""
        pass

    def _setup_rabbitmq_mocks(self):
        """Setup RabbitMQ connection mocks"""
        # Mock pika connection
        mock_connection = MagicMock(spec=pika.BlockingConnection)
        mock_channel = MagicMock(spec=pika.channel.Channel)
        mock_connection.channel.return_value = mock_channel

        # Store mocks for test access
        self.mocks['rabbitmq_connection'] = mock_connection
        self.mocks['rabbitmq_channel'] = mock_channel

        # Patch pika.BlockingConnection
        pika_patch = patch('pika.BlockingConnection', return_value=mock_connection)
        self.patches.append(pika_patch)
        pika_patch.start()

        # Setup default behaviors
        mock_channel.queue_declare.return_value = MagicMock(
            method=MagicMock(message_count=0, consumer_count=0)
        )
        mock_channel.basic_publish.return_value = None
        mock_channel.basic_consume.return_value = None

    def _setup_browser_mocks(self):
        """Setup Playwright browser mocks"""
        # Mock page object
        mock_page = AsyncMock()
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.query_selector.return_value = AsyncMock()
        mock_page.query_selector_all.return_value = []
        mock_page.evaluate.return_value = None
        mock_page.on.return_value = None
        mock_page.url = "https://x.com/home"
        mock_page.text_content.return_value = ""

        # Mock browser context
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_context.add_cookies.return_value = None

        # Mock browser
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        # Mock playwright
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        self.mocks['playwright'] = mock_playwright
        self.mocks['browser'] = mock_browser
        self.mocks['context'] = mock_context
        self.mocks['page'] = mock_page

    def _setup_cookie_mocks(self):
        """Setup cookie handling mocks"""
        # Mock cookie data
        self.mock_cookies = [
            {
                'name': 'auth_token',
                'value': 'test_auth_token',
                'domain': '.x.com',
                'path': '/',
                'secure': True,
                'httpOnly': True,
                'sameSite': 'Lax',
                'expires': int((datetime.now().timestamp() + 86400))
            },
            {
                'name': 'ct0',
                'value': 'test_csrf_token',
                'domain': '.x.com',
                'path': '/',
                'secure': True,
                'httpOnly': False,
                'sameSite': 'Lax'
            }
        ]

        # Mock file operations
        mock_open = patch('builtins.open', create=True)
        self.patches.append(mock_open)
        mock_file = mock_open.start()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(self.mock_cookies)

    def assert_message_published(self, exchange: str, routing_key: str, body: Dict[str, Any]):
        """Assert a message was published to RabbitMQ"""
        channel = self.mocks['rabbitmq_channel']
        channel.basic_publish.assert_called()

        # Find matching call
        for call in channel.basic_publish.call_args_list:
            args, kwargs = call
            if kwargs.get('exchange') == exchange and kwargs.get('routing_key') == routing_key:
                published_body = json.loads(kwargs.get('body', '{}'))
                for key, value in body.items():
                    assert published_body.get(key) == value, f"Message body mismatch for key {key}"
                return True

        assert False, f"No message published to {exchange} with routing key {routing_key}"

    def assert_queue_created(self, queue_name: str, durable: bool = True):
        """Assert a queue was created"""
        channel = self.mocks['rabbitmq_channel']
        channel.queue_declare.assert_called()

        for call in channel.queue_declare.call_args_list:
            args, kwargs = call
            if kwargs.get('queue') == queue_name:
                assert kwargs.get('durable') == durable, f"Queue durability mismatch"
                return True

        assert False, f"Queue {queue_name} was not created"

    def assert_page_navigated(self, url_pattern: str):
        """Assert browser navigated to URL"""
        page = self.mocks['page']
        page.goto.assert_called()

        for call in page.goto.call_args_list:
            args, _ = call
            if url_pattern in args[0]:
                return True

        assert False, f"Page did not navigate to URL matching {url_pattern}"

    def create_mock_notification(self, notif_type: str = "follow", from_handle: str = "testuser") -> Dict[str, Any]:
        """Create a mock notification for testing"""
        return {
            "notification_id": f"notif_{datetime.now().timestamp()}",
            "type": notif_type,
            "timestamp": datetime.now().isoformat(),
            "from_handle": from_handle,
            "from_name": f"Test User {from_handle}",
            "content": f"Test content for {notif_type}",
            "mentioned_users": [f"@{from_handle}"] if notif_type == "mention" else [],
            "raw_text": f"Raw notification text for {notif_type}"
        }

    def create_mock_bot_message(self, msg_type: str = "notification") -> Dict[str, Any]:
        """Create a mock BotMessage for testing"""
        return {
            "message_id": f"msg_{datetime.now().timestamp()}",
            "message_type": msg_type,
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "data": {
                "test_key": "test_value",
                "unicode_test": "🎉 Unicode test 你好"
            },
            "metadata": {
                "test_meta": "metadata"
            }
        }


class AsyncBaseTestFixture(BaseTestFixture):
    """Base fixture for async tests"""

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests"""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    async def async_setup(self):
        """Async setup - override in subclasses"""
        pass

    async def async_teardown(self):
        """Async teardown - override in subclasses"""
        pass

    def setup_method(self):
        """Setup with async support"""
        super().setup_method()
        asyncio.run(self.async_setup())

    def teardown_method(self):
        """Teardown with async support"""
        asyncio.run(self.async_teardown())
        super().teardown_method()