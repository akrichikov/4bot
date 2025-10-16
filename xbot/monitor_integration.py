"""
Integration module for connecting event monitoring with existing xbot automation.
Bridges the event interceptor with browser automation and media handling.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .event_interceptor import EventInterceptor, PostEvent, PatternSubscription
from .notifications import NotificationHandler, NotificationFilter
from .browser import BrowserManager
from .flows.media import download_media_from_post

logger = logging.getLogger(__name__)


class MonitorIntegration:
    """Integrates event monitoring with xbot automation features."""

    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_manager = browser_manager
        self.interceptor = EventInterceptor()
        self.notification_handler = None
        self.media_download_enabled = False
        self.auto_interact_enabled = False
        self.interaction_rules = {}

    async def setup_from_existing_browser(self, page):
        """Setup monitoring on an already authenticated browser page."""
        logger.info("Setting up event monitoring on existing browser session")

        # Initialize notification handler
        self.notification_handler = NotificationHandler({
            'console_output': True,
            'desktop_notifications': True,
            'log_file': f'xbot_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        })

        # Start monitoring
        await self.interceptor.start_monitoring(page)
        logger.info("Event monitoring active on existing session")

    async def add_media_download_subscription(self, authors: List[str] = None):
        """Add subscription to automatically download media from specific authors."""
        self.media_download_enabled = True

        async def media_callback(post: PostEvent):
            if post.has_media:
                if authors is None or post.author_handle.lower() in [a.lower() for a in authors]:
                    logger.info(f"Downloading media from @{post.author_handle}")
                    await self._download_post_media(post)

        subscription = PatternSubscription(
            id=f"media_download_{datetime.now().timestamp()}",
            name="Media Download",
            authors=set(authors) if authors else set(),
            callback=media_callback,
            active=True
        )

        self.interceptor.add_subscription(subscription)
        logger.info(f"Added media download subscription for: {authors or 'all authors'}")

    async def add_auto_interaction_subscription(self, rules: Dict[str, Any]):
        """Add subscription for automatic post interactions based on rules."""
        self.auto_interact_enabled = True
        self.interaction_rules = rules

        async def interaction_callback(post: PostEvent):
            if await self._should_interact(post, rules):
                await self._interact_with_post(post, rules)

        subscription = PatternSubscription(
            id=f"auto_interact_{datetime.now().timestamp()}",
            name="Auto Interaction",
            keywords=set(rules.get('keywords', [])),
            authors=set(rules.get('authors', [])),
            callback=interaction_callback,
            active=True
        )

        self.interceptor.add_subscription(subscription)
        logger.info(f"Added auto-interaction subscription with rules: {rules}")

    async def _download_post_media(self, post: PostEvent):
        """Download media from a post."""
        if not post.media_urls:
            return

        download_dir = Path("downloaded_media") / post.author_handle / post.id
        download_dir.mkdir(parents=True, exist_ok=True)

        for i, media_url in enumerate(post.media_urls):
            try:
                # Use the media flow's download function
                file_path = await download_media_from_post(
                    media_url,
                    download_dir / f"media_{i+1}",
                    post.author_handle
                )
                logger.info(f"Downloaded: {file_path}")
            except Exception as e:
                logger.error(f"Failed to download media: {e}")

        # Save post metadata
        metadata_file = download_dir / "post_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'id': post.id,
                'author': post.author,
                'author_handle': post.author_handle,
                'content': post.content,
                'timestamp': post.timestamp.isoformat(),
                'media_urls': post.media_urls,
                'likes': post.likes,
                'retweets': post.retweets
            }, f, indent=2)

    async def _should_interact(self, post: PostEvent, rules: Dict[str, Any]) -> bool:
        """Determine if we should interact with a post based on rules."""
        # Check engagement thresholds
        min_likes = rules.get('min_likes', 0)
        min_retweets = rules.get('min_retweets', 0)

        if post.likes < min_likes or post.retweets < min_retweets:
            return False

        # Check if author is in whitelist
        whitelist = rules.get('author_whitelist', [])
        if whitelist and post.author_handle.lower() not in [a.lower() for a in whitelist]:
            return False

        # Check if author is in blacklist
        blacklist = rules.get('author_blacklist', [])
        if post.author_handle.lower() in [a.lower() for a in blacklist]:
            return False

        # Check content filters
        must_contain = rules.get('must_contain', [])
        if must_contain:
            content_lower = post.content.lower()
            if not any(word.lower() in content_lower for word in must_contain):
                return False

        return True

    async def _interact_with_post(self, post: PostEvent, rules: Dict[str, Any]):
        """Interact with a post based on rules."""
        interactions = []

        if rules.get('auto_like', False):
            interactions.append('like')

        if rules.get('auto_retweet', False):
            interactions.append('retweet')

        if rules.get('auto_reply', False):
            reply_text = rules.get('reply_template', '').format(
                author=post.author,
                handle=post.author_handle
            )
            if reply_text:
                interactions.append(f'reply: {reply_text}')

        logger.info(f"Would interact with post {post.id}: {interactions}")
        # Note: Actual interaction would require browser automation methods

    async def create_monitoring_session(self, config: Dict[str, Any]):
        """Create a complete monitoring session with all features."""
        logger.info("Creating integrated monitoring session")

        # Setup notification handler
        self.notification_handler = NotificationHandler(config.get('notifications', {}))

        # Setup filters
        filter_config = config.get('filters', {})
        notification_filter = NotificationFilter()
        for key, value in filter_config.items():
            setattr(notification_filter, key, value)

        # Add configured subscriptions
        for sub_config in config.get('subscriptions', []):
            await self._create_subscription(sub_config)

        # Enable features
        if config.get('features', {}).get('media_download'):
            await self.add_media_download_subscription(
                config['features']['media_download'].get('authors')
            )

        if config.get('features', {}).get('auto_interaction'):
            await self.add_auto_interaction_subscription(
                config['features']['auto_interaction']
            )

        logger.info("Monitoring session configured successfully")

    async def _create_subscription(self, sub_config: Dict[str, Any]):
        """Create a subscription from configuration."""
        sub_type = sub_config.get('type')

        if sub_type == 'keywords':
            from .event_interceptor import create_keyword_subscription
            subscription = create_keyword_subscription(
                name=sub_config['name'],
                keywords=sub_config['keywords'],
                callback=self._create_callback(sub_config['name'])
            )
        elif sub_type == 'authors':
            from .event_interceptor import create_author_subscription
            subscription = create_author_subscription(
                name=sub_config['name'],
                authors=sub_config['authors'],
                callback=self._create_callback(sub_config['name'])
            )
        elif sub_type == 'regex':
            from .event_interceptor import create_regex_subscription
            subscription = create_regex_subscription(
                name=sub_config['name'],
                patterns=sub_config['patterns'],
                callback=self._create_callback(sub_config['name'])
            )
        else:
            logger.warning(f"Unknown subscription type: {sub_type}")
            return

        self.interceptor.add_subscription(subscription)
        logger.info(f"Added subscription: {sub_config['name']}")

    def _create_callback(self, subscription_name: str):
        """Create a callback function for a subscription."""
        async def callback(post: PostEvent):
            logger.info(f"[{subscription_name}] Post from @{post.author_handle}")
            if self.notification_handler:
                await self.notification_handler.handle_post(post)

        return callback

    async def export_monitoring_data(self, output_file: str = None):
        """Export collected monitoring data."""
        if not self.notification_handler:
            logger.warning("No notification handler configured")
            return

        recent_posts = self.notification_handler.get_recent_posts()

        if output_file is None:
            output_file = f'monitoring_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_posts': len(recent_posts),
            'posts': [self._post_to_dict(p) for p in recent_posts]
        }

        # Add statistics
        if recent_posts:
            export_data['statistics'] = {
                'unique_authors': len(set(p.author_handle for p in recent_posts)),
                'posts_with_media': sum(1 for p in recent_posts if p.has_media),
                'total_likes': sum(p.likes for p in recent_posts),
                'total_retweets': sum(p.retweets for p in recent_posts),
                'avg_engagement': sum(p.likes + p.retweets for p in recent_posts) / len(recent_posts)
            }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported {len(recent_posts)} posts to {output_file}")
        return output_file

    def _post_to_dict(self, post: PostEvent) -> Dict[str, Any]:
        """Convert PostEvent to dictionary."""
        return {
            'id': post.id,
            'author': post.author,
            'author_handle': post.author_handle,
            'content': post.content,
            'timestamp': post.timestamp.isoformat(),
            'likes': post.likes,
            'retweets': post.retweets,
            'replies': post.replies,
            'has_media': post.has_media,
            'media_urls': post.media_urls,
            'is_retweet': post.is_retweet,
            'is_reply': post.is_reply
        }


# Example configuration schema
EXAMPLE_CONFIG = {
    "notifications": {
        "desktop_notifications": True,
        "console_output": True,
        "webhook_url": None,
        "log_file": "xbot_monitor.jsonl",
        "buffer_size": 100
    },
    "filters": {
        "min_likes": 10,
        "min_retweets": 5,
        "exclude_retweets": True,
        "exclude_replies": False
    },
    "subscriptions": [
        {
            "type": "keywords",
            "name": "Tech News",
            "keywords": ["AI", "machine learning", "GPT", "neural network"]
        },
        {
            "type": "authors",
            "name": "Tech Leaders",
            "authors": ["elonmusk", "sama", "karpathy"]
        },
        {
            "type": "regex",
            "name": "Crypto",
            "patterns": ["\\$BTC", "\\$ETH", "bitcoin", "ethereum"]
        }
    ],
    "features": {
        "media_download": {
            "enabled": True,
            "authors": ["specific_author1", "specific_author2"]
        },
        "auto_interaction": {
            "enabled": False,
            "auto_like": True,
            "auto_retweet": False,
            "min_likes": 100,
            "author_whitelist": ["trusted_author1"],
            "author_blacklist": ["spam_account"],
            "must_contain": ["important", "breaking"]
        }
    }
}