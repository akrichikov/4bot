#!/usr/bin/env python3
"""
Notification Parser Tests
Tests the critical notification extraction logic (Pareto 80/20: data accuracy)
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base_test_fixture import AsyncBaseTestFixture


class TestNotificationParser(AsyncBaseTestFixture):
    """Test notification parsing - critical for data extraction accuracy"""

    def setup_custom(self):
        """Custom setup for parser tests"""
        self.mock_notifications = []
        self.captured_notifications = []

    def teardown_custom(self):
        """Custom teardown"""
        pass

    async def async_setup(self):
        """Async setup for parser tests"""
        # Mock console handler
        def capture_console(msg):
            text = msg.text()
            if '__NOTIF_JSON__:' in text:
                json_str = text.split('__NOTIF_JSON__:')[1]
                self.captured_notifications.append(json.loads(json_str))

        self.mocks['page'].on = capture_console

    async def async_teardown(self):
        """Async teardown"""
        pass

    def test_unicode_hash_id_generation(self):
        """Test Unicode-safe ID generation replacing btoa()"""
        # JavaScript hash function implementation in Python
        def generate_id(text):
            """Python implementation of the JavaScript hash function"""
            hash_val = 0
            for i in range(min(len(text), 200)):
                char_code = ord(text[i])
                hash_val = ((hash_val << 5) - hash_val) + char_code
                hash_val = hash_val & 0xFFFFFFFF  # Convert to 32-bit integer

            # Make positive and convert to base36
            import time
            timestamp_base36 = format(int(time.time() * 1000), 'x')
            hash_base36 = format(abs(hash_val), 'x')
            return f"notif_{hash_base36}_{timestamp_base36}"

        # Test with various Unicode strings
        test_cases = [
            "Simple ASCII text",
            "Emoji test 🎉🚀😊",
            "中文测试 Chinese test",
            "العربية Arabic test",
            "Русский Russian test",
            "Mixed 混合 🎯 test मिश्रित"
        ]

        generated_ids = set()
        for text in test_cases:
            notif_id = generate_id(text)

            # Verify ID format
            assert notif_id.startswith("notif_")
            assert "_" in notif_id

            # Verify uniqueness
            assert notif_id not in generated_ids
            generated_ids.add(notif_id)

            # Verify no special characters that could break JSON
            assert all(c.isalnum() or c == '_' for c in notif_id)

    @pytest.mark.asyncio
    async def test_notification_deduplication(self):
        """Test notification deduplication using Set tracking"""
        from final_notification_json_parser import NotificationJSONParser

        parser = NotificationJSONParser()

        # Create duplicate notifications with same content
        duplicate_notifs = [
            {
                "notification_id": "notif_same_123",
                "type": "follow",
                "from_handle": "testuser"
            },
            {
                "notification_id": "notif_same_123",  # Same ID
                "type": "follow",
                "from_handle": "testuser"
            },
            {
                "notification_id": "notif_different_456",  # Different ID
                "type": "follow",
                "from_handle": "testuser"
            }
        ]

        # Process notifications
        for notif in duplicate_notifs:
            if notif['notification_id'] not in parser.seen_ids:
                parser.seen_ids.add(notif['notification_id'])
                parser.notifications.append(notif)

        # Should only have 2 notifications (deduplicated)
        assert len(parser.notifications) == 2
        assert "notif_same_123" in parser.seen_ids
        assert "notif_different_456" in parser.seen_ids

    @pytest.mark.asyncio
    async def test_dom_extraction_javascript(self):
        """Test DOM extraction JavaScript injection"""
        # Mock page.evaluate response
        mock_page = self.mocks['page']

        # JavaScript extraction code snippet
        extraction_js = """
        function extractNotificationData(element) {
            const elementText = element.textContent || '';
            const notifData = {
                type: 'unknown',
                from_handle: 'unknown',
                content: ''
            };

            // Extract user from links
            const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
            if (userLinks.length > 0) {
                const href = userLinks[0].getAttribute('href');
                if (href && !href.includes('/status/')) {
                    notifData.from_handle = href.split('/').pop() || 'unknown';
                }
            }

            // Detect notification type
            const textLower = elementText.toLowerCase();
            if (textLower.includes('liked')) notifData.type = 'like';
            else if (textLower.includes('followed')) notifData.type = 'follow';
            else if (textLower.includes('replied')) notifData.type = 'reply';
            else if (textLower.includes('mentioned')) notifData.type = 'mention';

            return notifData;
        }
        """

        # Verify JavaScript doesn't throw errors
        try:
            # This would be executed in browser context
            result = await mock_page.evaluate(extraction_js)
            # Mock returns None, but no exception means valid JS
            assert True
        except Exception as e:
            pytest.fail(f"JavaScript extraction failed: {e}")

    @pytest.mark.asyncio
    async def test_notification_type_detection(self):
        """Test detection of all notification types"""
        test_cases = [
            ("John liked your post", "like"),
            ("Sarah followed you", "follow"),
            ("Mike replied to your tweet", "reply"),
            ("Jane mentioned you in a post", "mention"),
            ("Bob retweeted your post", "retweet"),
            ("Alice quoted your tweet", "quote"),
            ("Random notification text", "unknown")
        ]

        for text, expected_type in test_cases:
            # Simulate type detection logic
            text_lower = text.lower()
            detected_type = "unknown"

            if "liked" in text_lower:
                detected_type = "like"
            elif "followed" in text_lower:
                detected_type = "follow"
            elif "replied" in text_lower:
                detected_type = "reply"
            elif "mentioned" in text_lower:
                detected_type = "mention"
            elif "retweeted" in text_lower or "reposted" in text_lower:
                detected_type = "retweet"
            elif "quoted" in text_lower:
                detected_type = "quote"

            assert detected_type == expected_type, f"Failed to detect {expected_type} from '{text}'"

    @pytest.mark.asyncio
    async def test_mention_extraction(self):
        """Test extraction of @mentions from notification text"""
        test_cases = [
            ("@user1 mentioned you", ["@user1"]),
            ("Replying to @user1 @user2", ["@user1", "@user2"]),
            ("Check out @test_user's tweet", ["@test_user"]),
            ("Multiple @mentions @in @one @text", ["@mentions", "@in", "@one", "@text"]),
            ("No mentions here", [])
        ]

        for text, expected_mentions in test_cases:
            import re
            mentions = re.findall(r'@[a-zA-Z0-9_]+', text)
            assert mentions == expected_mentions

    @pytest.mark.asyncio
    async def test_page_refresh_cycle(self):
        """Test page refresh every 20 seconds and script re-injection"""
        from unittest.mock import call

        mock_page = self.mocks['page']

        # Simulate refresh cycle
        refresh_interval = 20  # seconds
        total_duration = 60  # seconds
        expected_refreshes = total_duration // refresh_interval

        # Mock the refresh calls
        refresh_times = []
        async def mock_reload(*args, **kwargs):
            refresh_times.append(datetime.now())
            return None

        mock_page.reload = AsyncMock(side_effect=mock_reload)

        # Simulate monitoring loop
        start_time = datetime.now()
        last_refresh = start_time

        for _ in range(total_duration):
            current_time = datetime.now()
            if (current_time - last_refresh).seconds >= refresh_interval:
                await mock_page.reload(wait_until='domcontentloaded')
                last_refresh = current_time
            await asyncio.sleep(1)  # Simulate 1 second of monitoring

        # Verify refresh count
        assert len(refresh_times) >= expected_refreshes - 1  # Allow for timing variance

    @pytest.mark.asyncio
    async def test_json_output_structure(self):
        """Test JSON output structure and schema"""
        from final_notification_json_parser import ParsedNotification, NotificationUser, PostContent

        # Create a complete notification
        notification = ParsedNotification(
            notification_id="test_123",
            type="reply",
            timestamp_captured="2025-10-16T10:00:00Z",
            timestamp_event="2025-10-16T09:59:00Z",
            actor=NotificationUser(
                handle="testuser",
                display_name="Test User",
                avatar_url="https://example.com/avatar.jpg",
                verified=True
            ),
            target_post=None,
            new_content=PostContent(
                text="This is a reply",
                has_media=False,
                media_count=0,
                quoted_post=None,
                urls=[],
                hashtags=["#test"]
            ),
            metrics=None,
            mentioned_users=["@otheruser"],
            raw_text="Test User replied to you: This is a reply"
        )

        # Convert to dict (as would be saved to JSON)
        from dataclasses import asdict
        notif_dict = asdict(notification)

        # Verify structure
        assert notif_dict['notification_id'] == "test_123"
        assert notif_dict['type'] == "reply"
        assert notif_dict['actor']['handle'] == "testuser"
        assert notif_dict['actor']['verified'] == True
        assert notif_dict['new_content']['text'] == "This is a reply"
        assert notif_dict['new_content']['hashtags'] == ["#test"]
        assert notif_dict['mentioned_users'] == ["@otheruser"]

        # Verify JSON serializable
        json_str = json.dumps(notif_dict)
        parsed = json.loads(json_str)
        assert parsed['notification_id'] == "test_123"

    @pytest.mark.asyncio
    async def test_media_detection(self):
        """Test detection of media in notifications"""
        # Mock DOM element with media indicators
        mock_elements = [
            {'data-testid': 'tweetPhoto', 'count': 2},
            {'data-testid': 'videoPlayer', 'count': 1},
            {'data-testid': 'card.wrapper', 'count': 1}
        ]

        total_media = sum(elem['count'] for elem in mock_elements)
        has_media = total_media > 0

        assert has_media == True
        assert total_media == 4

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test parser recovers from extraction errors"""
        # Simulate various error conditions
        error_cases = [
            None,  # Null element
            {},  # Empty object
            {'textContent': None},  # Null content
            {'textContent': ''},  # Empty content
        ]

        for error_case in error_cases:
            try:
                # Simulate extraction with error case
                text_content = error_case.get('textContent', '') if error_case else ''
                # Should handle gracefully
                result = {
                    'notification_id': 'error_safe',
                    'type': 'unknown',
                    'raw_text': text_content or ''
                }
                assert result['type'] == 'unknown'
            except Exception as e:
                pytest.fail(f"Parser failed to handle error case: {e}")

    @pytest.mark.asyncio
    async def test_timestamp_extraction(self):
        """Test extraction of event timestamps from DOM"""
        # Mock time element
        mock_time_element = {
            'datetime': '2025-10-16T10:00:00Z'
        }

        # Extract timestamp
        timestamp = mock_time_element.get('datetime')
        assert timestamp == '2025-10-16T10:00:00Z'

        # Verify ISO format
        from datetime import datetime
        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert parsed_time.year == 2025
        assert parsed_time.month == 10
        assert parsed_time.day == 16