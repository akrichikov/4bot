#!/usr/bin/env python3
"""
Mock Factory Classes for Testing
Provides reusable, realistic test data following the Factory pattern (DRY principle)
"""

import random
import string
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class ParsedNotification:
    """Notification data structure"""
    notification_id: str
    type: str
    timestamp_captured: str
    timestamp_event: Optional[str]
    actor: Optional[Dict[str, Any]]
    target_post: Optional[Dict[str, Any]]
    new_content: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    mentioned_users: List[str]
    raw_text: str


@dataclass
class NotificationUser:
    """User information in notification"""
    handle: str
    display_name: str
    avatar_url: Optional[str]
    verified: bool


@dataclass
class PostContent:
    """Post content in notification"""
    text: str
    has_media: bool
    media_count: int
    quoted_post: Optional[Dict[str, Any]]
    urls: List[str]
    hashtags: List[str]


@dataclass
class BotMessage:
    """RabbitMQ message structure"""
    message_id: str
    message_type: str
    timestamp: str
    source: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class NotificationFactory:
    """Factory for generating realistic notification test data"""

    # Realistic user handles for testing
    VERIFIED_USERS = [
        "elonmusk", "BillGates", "sundarpichai", "satyanadella", "tim_cook",
        "jeffbezos", "WarrenBuffett", "katyperry", "rihanna", "cristiano"
    ]

    REGULAR_USERS = [
        "techie123", "crypto_trader", "ai_enthusiast", "startup_founder",
        "code_wizard", "data_scientist", "web3_builder", "product_manager",
        "ux_designer", "growth_hacker"
    ]

    # Realistic notification content templates
    REPLY_TEMPLATES = [
        "Great point! I totally agree with this perspective.",
        "Interesting take, but have you considered {alternative}?",
        "This is exactly what I've been saying! 💯",
        "Thanks for sharing this insight!",
        "Could you elaborate more on this?",
        "Brilliant analysis! 🚀",
    ]

    MENTION_TEMPLATES = [
        "Hey @{user}, check out this thread about {topic}",
        "cc @{user} @{user2} for visibility",
        "As @{user} mentioned earlier, this is crucial",
        "Shoutout to @{user} for the inspiration!",
        ".@{user} thoughts on this?",
    ]

    HASHTAGS = [
        "#AI", "#MachineLearning", "#Tech", "#Innovation", "#Startup",
        "#Web3", "#Blockchain", "#DataScience", "#Programming", "#Future",
        "#CloudComputing", "#Cybersecurity", "#DevOps", "#Python", "#JavaScript"
    ]

    @classmethod
    def create_follow_notification(cls, verified: bool = False) -> ParsedNotification:
        """Create a follow notification"""
        handle = random.choice(cls.VERIFIED_USERS if verified else cls.REGULAR_USERS)

        return ParsedNotification(
            notification_id=cls._generate_id(),
            type="follow",
            timestamp_captured=datetime.now().isoformat(),
            timestamp_event=(datetime.now() - timedelta(minutes=random.randint(1, 10))).isoformat(),
            actor=asdict(NotificationUser(
                handle=handle,
                display_name=cls._generate_display_name(handle),
                avatar_url=f"https://pbs.twimg.com/profile_images/{random.randint(1000000, 9999999)}/photo.jpg",
                verified=verified
            )),
            target_post=None,
            new_content=None,
            metrics=None,
            mentioned_users=[],
            raw_text=f"{cls._generate_display_name(handle)} followed you"
        )

    @classmethod
    def create_like_notification(cls, with_metrics: bool = True) -> ParsedNotification:
        """Create a like notification"""
        handle = random.choice(cls.VERIFIED_USERS + cls.REGULAR_USERS)

        metrics = None
        if with_metrics:
            metrics = {
                "likes": random.randint(1, 10000),
                "retweets": random.randint(0, 5000),
                "replies": random.randint(0, 1000),
                "views": random.randint(100, 1000000)
            }

        return ParsedNotification(
            notification_id=cls._generate_id(),
            type="like",
            timestamp_captured=datetime.now().isoformat(),
            timestamp_event=(datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat(),
            actor=asdict(NotificationUser(
                handle=handle,
                display_name=cls._generate_display_name(handle),
                avatar_url=f"https://pbs.twimg.com/profile_images/{random.randint(1000000, 9999999)}/photo.jpg",
                verified=handle in cls.VERIFIED_USERS
            )),
            target_post={
                "post_id": cls._generate_post_id(),
                "content": "Your original tweet content here"
            },
            new_content=None,
            metrics=metrics,
            mentioned_users=[],
            raw_text=f"{cls._generate_display_name(handle)} liked your post"
        )

    @classmethod
    def create_reply_notification(cls, with_media: bool = False) -> ParsedNotification:
        """Create a reply notification"""
        handle = random.choice(cls.VERIFIED_USERS + cls.REGULAR_USERS)
        reply_text = random.choice(cls.REPLY_TEMPLATES).format(
            alternative="a different approach"
        )

        hashtags = random.sample(cls.HASHTAGS, k=random.randint(0, 3))

        return ParsedNotification(
            notification_id=cls._generate_id(),
            type="reply",
            timestamp_captured=datetime.now().isoformat(),
            timestamp_event=(datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
            actor=asdict(NotificationUser(
                handle=handle,
                display_name=cls._generate_display_name(handle),
                avatar_url=f"https://pbs.twimg.com/profile_images/{random.randint(1000000, 9999999)}/photo.jpg",
                verified=handle in cls.VERIFIED_USERS
            )),
            target_post={
                "post_id": cls._generate_post_id(),
                "content": "Your original tweet"
            },
            new_content=asdict(PostContent(
                text=reply_text,
                has_media=with_media,
                media_count=random.randint(1, 4) if with_media else 0,
                quoted_post=None,
                urls=["https://example.com/article"] if random.random() > 0.7 else [],
                hashtags=hashtags
            )),
            metrics=None,
            mentioned_users=[f"@{random.choice(cls.REGULAR_USERS)}"] if random.random() > 0.5 else [],
            raw_text=f"{cls._generate_display_name(handle)} replied: {reply_text}"
        )

    @classmethod
    def create_mention_notification(cls, multiple_mentions: bool = False) -> ParsedNotification:
        """Create a mention notification"""
        handle = random.choice(cls.VERIFIED_USERS + cls.REGULAR_USERS)

        mentioned = ["@you"]
        if multiple_mentions:
            mentioned.extend([f"@{u}" for u in random.sample(cls.REGULAR_USERS, k=random.randint(1, 3))])

        mention_text = random.choice(cls.MENTION_TEMPLATES).format(
            user="you",
            user2=random.choice(cls.REGULAR_USERS),
            topic="AI developments"
        )

        return ParsedNotification(
            notification_id=cls._generate_id(),
            type="mention",
            timestamp_captured=datetime.now().isoformat(),
            timestamp_event=(datetime.now() - timedelta(minutes=random.randint(1, 120))).isoformat(),
            actor=asdict(NotificationUser(
                handle=handle,
                display_name=cls._generate_display_name(handle),
                avatar_url=f"https://pbs.twimg.com/profile_images/{random.randint(1000000, 9999999)}/photo.jpg",
                verified=handle in cls.VERIFIED_USERS
            )),
            target_post=None,
            new_content=asdict(PostContent(
                text=mention_text,
                has_media=False,
                media_count=0,
                quoted_post=None,
                urls=[],
                hashtags=random.sample(cls.HASHTAGS, k=random.randint(1, 2))
            )),
            metrics=None,
            mentioned_users=mentioned,
            raw_text=f"{cls._generate_display_name(handle)} mentioned you: {mention_text}"
        )

    @classmethod
    def create_unicode_notification(cls) -> ParsedNotification:
        """Create notification with Unicode characters for testing"""
        unicode_handles = ["emoji_user_🎉", "中文用户", "العربية", "हिन्दी", "русский"]
        handle = random.choice(unicode_handles)

        unicode_texts = [
            "Great work! 🎉🚀🔥",
            "你好！这太棒了 👍",
            "مرحبا! رائع جدا ⭐",
            "Отлично! Молодец! 💪",
            "बहुत अच्छा! 🙏"
        ]

        return ParsedNotification(
            notification_id=cls._generate_id(),
            type=random.choice(["like", "reply", "mention"]),
            timestamp_captured=datetime.now().isoformat(),
            timestamp_event=datetime.now().isoformat(),
            actor=asdict(NotificationUser(
                handle=handle,
                display_name=f"Unicode Test {handle}",
                avatar_url=None,
                verified=False
            )),
            target_post=None,
            new_content=asdict(PostContent(
                text=random.choice(unicode_texts),
                has_media=False,
                media_count=0,
                quoted_post=None,
                urls=[],
                hashtags=["#Unicode测试", "#🎉"]
            )),
            metrics=None,
            mentioned_users=[],
            raw_text=f"{handle}: {random.choice(unicode_texts)}"
        )

    @staticmethod
    def _generate_id() -> str:
        """Generate unique notification ID"""
        timestamp = int(time.time() * 1000)
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"notif_{random_part}_{timestamp}"

    @staticmethod
    def _generate_post_id() -> str:
        """Generate realistic post ID"""
        return str(random.randint(1000000000000000000, 9999999999999999999))

    @staticmethod
    def _generate_display_name(handle: str) -> str:
        """Generate display name from handle"""
        if handle in NotificationFactory.VERIFIED_USERS:
            names = {
                "elonmusk": "Elon Musk",
                "BillGates": "Bill Gates",
                "sundarpichai": "Sundar Pichai",
                "satyanadella": "Satya Nadella",
                "tim_cook": "Tim Cook",
                "jeffbezos": "Jeff Bezos",
                "WarrenBuffett": "Warren Buffett",
                "katyperry": "Katy Perry",
                "rihanna": "Rihanna",
                "cristiano": "Cristiano Ronaldo"
            }
            return names.get(handle, handle.replace("_", " ").title())
        return handle.replace("_", " ").title()


class CookieFactory:
    """Factory for generating realistic cookie test data"""

    COOKIE_NAMES = {
        "auth": ["auth_token", "auth_multi", "auth"],
        "session": ["ct0", "kdt", "sess", "session_id"],
        "tracking": ["guest_id", "personalization_id", "g_state"],
        "preferences": ["lang", "timezone", "theme"],
        "security": ["csrf_token", "twid", "_twitter_sess"]
    }

    DOMAINS = [".x.com", ".twitter.com", "api.x.com", "api.twitter.com"]

    @classmethod
    def create_auth_cookie(cls, expired: bool = False) -> Dict[str, Any]:
        """Create authentication cookie"""
        expiry_time = datetime.now() + (timedelta(days=-30) if expired else timedelta(days=30))

        return {
            "name": random.choice(cls.COOKIE_NAMES["auth"]),
            "value": cls._generate_token(32),
            "domain": random.choice(cls.DOMAINS[:2]),  # Only root domains for auth
            "path": "/",
            "expires": int(expiry_time.timestamp()),
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }

    @classmethod
    def create_session_cookie(cls) -> Dict[str, Any]:
        """Create session cookie (no expiry)"""
        return {
            "name": random.choice(cls.COOKIE_NAMES["session"]),
            "value": cls._generate_token(24),
            "domain": random.choice(cls.DOMAINS[:2]),
            "path": "/",
            # No expires for session cookie
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict"
        }

    @classmethod
    def create_tracking_cookie(cls) -> Dict[str, Any]:
        """Create tracking cookie"""
        return {
            "name": random.choice(cls.COOKIE_NAMES["tracking"]),
            "value": cls._generate_token(16),
            "domain": random.choice(cls.DOMAINS),
            "path": "/",
            "expires": int((datetime.now() + timedelta(days=365)).timestamp()),
            "httpOnly": False,
            "secure": True,
            "sameSite": "None"
        }

    @classmethod
    def create_chrome_format_cookie(cls) -> Dict[str, Any]:
        """Create cookie in Chrome export format"""
        return {
            "name": random.choice(sum(cls.COOKIE_NAMES.values(), [])),
            "value": cls._generate_token(20),
            "domain": random.choice(cls.DOMAINS),
            "path": "/",
            "expirationDate": (datetime.now() + timedelta(days=7)).timestamp(),  # Float
            "httponly": random.randint(0, 1),  # Numeric boolean
            "secure": 1,  # Numeric boolean
            "sameSite": "lax"  # Lowercase
        }

    @classmethod
    def create_unicode_cookie(cls) -> Dict[str, Any]:
        """Create cookie with Unicode values"""
        unicode_values = [
            "token_🔐_secure",
            "认证_令牌",
            "مفتاح_الأمان",
            "ключ_безопасности"
        ]

        return {
            "name": "unicode_test",
            "value": random.choice(unicode_values),
            "domain": ".x.com",
            "path": "/",
            "expires": int((datetime.now() + timedelta(days=1)).timestamp()),
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        }

    @classmethod
    def create_cookie_set(cls, count: int = 5, profile: str = "default") -> List[Dict[str, Any]]:
        """Create a set of cookies for a profile"""
        cookies = []

        # Always include essential cookies
        cookies.append(cls.create_auth_cookie())
        cookies.append(cls.create_session_cookie())

        # Add random additional cookies
        for _ in range(count - 2):
            cookie_type = random.choice([
                cls.create_tracking_cookie,
                cls.create_auth_cookie,
                cls.create_session_cookie
            ])
            cookies.append(cookie_type())

        # Add profile identifier
        for cookie in cookies:
            cookie["_profile"] = profile

        return cookies

    @staticmethod
    def _generate_token(length: int) -> str:
        """Generate random token string"""
        chars = string.ascii_letters + string.digits + "-_"
        return ''.join(random.choices(chars, k=length))


class MessageFactory:
    """Factory for generating RabbitMQ message test data"""

    MESSAGE_TYPES = ["notification", "command", "response", "error", "status"]
    SOURCES = ["twitter", "system", "user", "scheduler", "webhook"]

    COMMAND_TYPES = [
        "post_tweet", "follow_user", "like_post", "reply_to_post",
        "retweet", "quote_tweet", "send_dm", "update_bio"
    ]

    @classmethod
    def create_notification_message(cls, notification: Optional[ParsedNotification] = None) -> BotMessage:
        """Create notification message from ParsedNotification"""
        if notification is None:
            notification = NotificationFactory.create_follow_notification()

        return BotMessage(
            message_id=cls._generate_message_id(),
            message_type="notification",
            timestamp=datetime.now().isoformat(),
            source="twitter",
            data=asdict(notification),
            metadata={
                "retry_count": 0,
                "priority": "normal",
                "processed": False
            }
        )

    @classmethod
    def create_command_message(cls, command: Optional[str] = None) -> BotMessage:
        """Create command message"""
        if command is None:
            command = random.choice(cls.COMMAND_TYPES)

        parameters = cls._get_command_parameters(command)

        return BotMessage(
            message_id=cls._generate_message_id(),
            message_type="command",
            timestamp=datetime.now().isoformat(),
            source="user",
            data={
                "command": command,
                "parameters": parameters
            },
            metadata={
                "user_id": f"user_{random.randint(1000, 9999)}",
                "session_id": cls._generate_token(16)
            }
        )

    @classmethod
    def create_error_message(cls, error_type: str = "generic") -> BotMessage:
        """Create error message"""
        error_types = {
            "generic": "An unexpected error occurred",
            "auth": "Authentication failed: Invalid credentials",
            "rate_limit": "Rate limit exceeded. Please try again later",
            "network": "Network error: Connection timeout",
            "parse": "Failed to parse notification data"
        }

        return BotMessage(
            message_id=cls._generate_message_id(),
            message_type="error",
            timestamp=datetime.now().isoformat(),
            source="system",
            data={
                "error_type": error_type,
                "message": error_types.get(error_type, "Unknown error"),
                "stack_trace": cls._generate_stack_trace() if random.random() > 0.5 else None
            },
            metadata={
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "recoverable": random.choice([True, False])
            }
        )

    @classmethod
    def create_large_message(cls, size_kb: int = 100) -> BotMessage:
        """Create message with large payload for testing"""
        # Generate large text content
        large_text = "X" * (size_kb * 1024)

        return BotMessage(
            message_id=cls._generate_message_id(),
            message_type="notification",
            timestamp=datetime.now().isoformat(),
            source="test",
            data={
                "large_content": large_text,
                "size_kb": size_kb
            }
        )

    @classmethod
    def create_unicode_message(cls) -> BotMessage:
        """Create message with Unicode content"""
        unicode_data = {
            "emoji": "🎉🚀🔥✨🌟",
            "chinese": "你好世界 - 测试消息",
            "arabic": "مرحبا بالعالم - رسالة اختبار",
            "japanese": "こんにちは世界 - テストメッセージ",
            "russian": "Привет мир - тестовое сообщение",
            "mixed": "Hello 世界 🌍 مرحبا"
        }

        return BotMessage(
            message_id=cls._generate_message_id(),
            message_type="notification",
            timestamp=datetime.now().isoformat(),
            source="test",
            data=unicode_data,
            metadata={"charset": "utf-8"}
        )

    @classmethod
    def create_malformed_json_strings(cls) -> List[str]:
        """Create malformed JSON strings for error testing"""
        return [
            '{"incomplete": ',
            '{"key": undefined}',
            '{"nested": {"broken"',
            'not json at all',
            '{"dup": "key", "dup": "key"}',
            '{"trailing": "comma",}',
            "{'single': 'quotes'}",
            '{"unescaped": "quote"here"}',
            '{"null": null, "nan": NaN}',
            ''  # Empty string
        ]

    @staticmethod
    def _generate_message_id() -> str:
        """Generate unique message ID"""
        timestamp = int(time.time() * 1000000)  # Microseconds
        random_part = ''.join(random.choices(string.hexdigits.lower(), k=8))
        return f"msg_{timestamp}_{random_part}"

    @staticmethod
    def _generate_token(length: int) -> str:
        """Generate random token"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def _get_command_parameters(command: str) -> Dict[str, Any]:
        """Get appropriate parameters for command type"""
        params = {
            "post_tweet": {
                "content": f"Test tweet at {datetime.now().strftime('%H:%M:%S')}",
                "media": []
            },
            "follow_user": {
                "username": random.choice(NotificationFactory.REGULAR_USERS)
            },
            "like_post": {
                "post_id": str(random.randint(1000000000000000000, 9999999999999999999))
            },
            "reply_to_post": {
                "post_id": str(random.randint(1000000000000000000, 9999999999999999999)),
                "content": "Great point!"
            },
            "retweet": {
                "post_id": str(random.randint(1000000000000000000, 9999999999999999999))
            },
            "quote_tweet": {
                "post_id": str(random.randint(1000000000000000000, 9999999999999999999)),
                "content": "Adding my thoughts..."
            },
            "send_dm": {
                "recipient": random.choice(NotificationFactory.REGULAR_USERS),
                "message": "Hey, check this out!"
            },
            "update_bio": {
                "bio": "AI enthusiast | Building cool stuff | 🚀"
            }
        }
        return params.get(command, {})

    @staticmethod
    def _generate_stack_trace() -> str:
        """Generate mock stack trace"""
        return """Traceback (most recent call last):
  File "rabbitmq_manager.py", line 123, in process_message
    handler(message)
  File "notification_handler.py", line 45, in handle_notification
    parse_notification(data)
  File "parser.py", line 67, in parse_notification
    raise ValueError("Invalid notification format")
ValueError: Invalid notification format"""