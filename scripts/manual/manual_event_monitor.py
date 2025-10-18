#!/usr/bin/env python3
"""
Test implementation of the X/Twitter event monitoring system.
Demonstrates real-time post interception with pattern-based notifications.
"""

import asyncio
from typing import Any as _Moved
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from xbot.event_interceptor import (
    EventInterceptor,
    create_keyword_subscription,
    create_author_subscription,
    create_regex_subscription,
    PostEvent
)
from xbot.notifications import NotificationHandler, NotificationAggregator, NotificationFilter

# Configure logging
logs_dir = Path('logs')
logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(logs_dir / 'event_monitor.log'))
    ]
)
logger = logging.getLogger(__name__)


class XEventMonitor:
    """Complete X/Twitter event monitoring system."""

    def __init__(self):
        self.interceptor = EventInterceptor()
        self.notification_config = {
            'desktop_notifications': True,
            'console_output': True,
            'webhook_url': None,  # Set to your webhook URL if needed
            'log_file': 'notifications.jsonl',
            'buffer_size': 50
        }
        self.notification_handler = NotificationHandler(self.notification_config)
        self.notification_filter = NotificationFilter()
        self.browser = None
        self.context = None
        self.page = None

    async def load_cookies(self):
        """Load cookies from saved file."""
        cookie_file = Path('auth_data/x_cookies.json')
        if not cookie_file.exists():
            raise FileNotFoundError(f"Cookie file not found: {cookie_file}")

        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        logger.info(f"Loaded {len(cookies)} cookies")
        return cookies

    async def setup_browser(self):
        """Set up browser with cookies and monitoring."""
        playwright = await async_playwright().start()

        # Launch browser
        self.browser = await playwright.chromium.launch(
            headless=False,  # Set to True for background monitoring
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox'
            ]
        )

        # Create context with viewport and user agent
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Load and add cookies
        cookies = await self.load_cookies()
        await self.context.add_cookies(cookies)

        # Create page
        self.page = await self.context.new_page()

        # Navigate to X/Twitter
        logger.info("Navigating to X/Twitter...")
        await self.page.goto('https://x.com/home', wait_until='networkidle')

        # Wait for feed to load
        await self.page.wait_for_selector('article', timeout=30000)
        logger.info("Feed loaded successfully")

    async def setup_subscriptions(self):
        """Set up pattern subscriptions for monitoring."""

        # Example 1: Monitor specific keywords
        keyword_sub = create_keyword_subscription(
            name="Tech Keywords",
            keywords=["AI", "machine learning", "GPT", "LLM", "neural", "blockchain"],
            callback=self.on_tech_post
        )
        self.interceptor.add_subscription(keyword_sub)

        # Example 2: Monitor specific authors
        author_sub = create_author_subscription(
            name="Notable Authors",
            authors=["elonmusk", "sama", "karpathy", "ylecun"],  # Add handles without @
            callback=self.on_notable_author
        )
        self.interceptor.add_subscription(author_sub)

        # Example 3: Monitor with regex patterns
        regex_sub = create_regex_subscription(
            name="Links and Mentions",
            patterns=[
                r"https?://\S+",  # URLs
                r"@\w+",  # Mentions
                r"#\w+",  # Hashtags
                r"\$[A-Z]{2,5}",  # Stock tickers
            ],
            callback=self.on_pattern_match
        )
        self.interceptor.add_subscription(regex_sub)

        # Add global callback for all posts
        self.interceptor.add_callback(self.on_any_post)

        logger.info(f"Set up {len(self.interceptor.subscriptions)} subscriptions")

    async def on_tech_post(self, post: PostEvent):
        """Handle tech-related posts."""
        logger.info(f"📱 TECH POST: @{post.author_handle}: {post.content[:100]}...")
        await self.notification_handler.handle_post(post)

    async def on_notable_author(self, post: PostEvent):
        """Handle posts from notable authors."""
        logger.info(f"⭐ NOTABLE AUTHOR: @{post.author_handle}: {post.content[:100]}...")
        await self.notification_handler.handle_post(post)

    async def on_pattern_match(self, post: PostEvent):
        """Handle posts matching patterns."""
        logger.info(f"🔍 PATTERN MATCH: @{post.author_handle}: {post.content[:100]}...")

    async def on_any_post(self, post: PostEvent):
        """Handle any post (global callback)."""
        # Apply filter before processing
        if self.notification_filter.should_notify(post):
            logger.debug(f"New post from @{post.author_handle} (ID: {post.id})")

    async def configure_filter(self, min_likes=0, min_retweets=0, require_media=False):
        """Configure notification filter settings."""
        self.notification_filter.min_likes = min_likes
        self.notification_filter.min_retweets = min_retweets
        self.notification_filter.require_media = require_media
        self.notification_filter.exclude_retweets = True  # Skip retweets
        self.notification_filter.exclude_replies = False  # Include replies

        logger.info(f"Filter configured: min_likes={min_likes}, min_retweets={min_retweets}, require_media={require_media}")

    async def start_monitoring(self):
        """Start the monitoring system."""
        try:
            # Setup browser and navigation
            await self.setup_browser()

            # Setup subscriptions
            await self.setup_subscriptions()

            # Configure filter (optional)
            await self.configure_filter(min_likes=10, require_media=False)

            # Start notification handler context
            async with self.notification_handler:
                # Start monitoring
                await self.interceptor.start_monitoring(self.page)

                logger.info("🚀 Monitoring started! Press Ctrl+C to stop...")

                # Keep monitoring until interrupted
                try:
                    while True:
                        # Scroll periodically to load new posts
                        await asyncio.sleep(30)
                        await self.page.evaluate("window.scrollBy(0, 500)")
                        logger.debug("Scrolled to load new posts...")

                        # Get recent posts from buffer
                        recent = self.notification_handler.get_recent_posts(5)
                        if recent:
                            logger.info(f"📊 Buffer has {len(recent)} recent posts")

                except KeyboardInterrupt:
                    logger.info("Stopping monitor...")

        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        if self.page:
            await self.interceptor.stop_monitoring(self.page)
        if self.browser:
            await self.browser.close()
        logger.info("Cleanup completed")

    async def test_with_aggregation(self):
        """Test with notification aggregation (batch mode)."""
        try:
            # Setup browser
            await self.setup_browser()
            await self.setup_subscriptions()

            # Create aggregator for batch processing
            aggregator = NotificationAggregator(
                self.notification_handler,
                interval_seconds=60  # Batch every minute
            )

            # Replace direct handler with aggregated processing
            async def aggregated_callback(post: PostEvent):
                await aggregator.add_post(post)

            # Override callbacks to use aggregator
            self.interceptor.callbacks = [aggregated_callback]

            async with self.notification_handler:
                await aggregator.start()
                await self.interceptor.start_monitoring(self.page)

                logger.info("🚀 Batch monitoring started (60s intervals)...")

                try:
                    await asyncio.sleep(300)  # Monitor for 5 minutes
                except KeyboardInterrupt:
                    pass

                await aggregator.stop()

        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    monitor = XEventMonitor()

    # Choose monitoring mode
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    if mode == "batch":
        logger.info("Starting in BATCH mode (aggregated notifications)")
        await monitor.test_with_aggregation()
    else:
        logger.info("Starting in NORMAL mode (instant notifications)")
        await monitor.start_monitoring()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     X/Twitter Real-Time Event Monitor            ║
    ╠══════════════════════════════════════════════════╣
    ║  Usage:                                          ║
    ║    python test_event_monitor.py [mode]          ║
    ║                                                  ║
    ║  Modes:                                          ║
    ║    normal - Instant notifications (default)     ║
    ║    batch  - Aggregated notifications (60s)      ║
    ╚══════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
