"""
Notification system for intercepted X/Twitter posts.
Handles desktop notifications, logging, and webhooks.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import aiohttp
from dataclasses import asdict

from .event_interceptor import PostEvent

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handles notifications for intercepted posts."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.log_file = Path(self.config.get('log_file', 'notifications.jsonl'))
        self.webhook_url = self.config.get('webhook_url')
        self.desktop_notifications = self.config.get('desktop_notifications', True)
        self.console_output = self.config.get('console_output', True)
        self.buffer: List[PostEvent] = []
        self.buffer_size = self.config.get('buffer_size', 10)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def handle_post(self, post: PostEvent) -> None:
        """Handle a new post notification."""
        # Add to buffer
        self.buffer.append(post)
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)

        # Execute notifications concurrently
        tasks = []

        if self.console_output:
            tasks.append(self._console_notification(post))

        if self.desktop_notifications:
            tasks.append(self._desktop_notification(post))

        if self.webhook_url:
            tasks.append(self._webhook_notification(post))

        # Always log
        tasks.append(self._log_notification(post))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _console_notification(self, post: PostEvent) -> None:
        """Output notification to console."""
        timestamp = post.timestamp.strftime('%H:%M:%S')
        print(f"\n{'=' * 70}")
        print(f"📢 NEW POST DETECTED at {timestamp}")
        print(f"👤 Author: {post.author} (@{post.author_handle})")
        print(f"💬 Content: {post.content[:200]}{'...' if len(post.content) > 200 else ''}")
        print(f"📊 Stats: 💙 {post.likes} | 🔄 {post.retweets} | 💬 {post.replies}")
        if post.has_media:
            print(f"📷 Media: {len(post.media_urls)} item(s)")
        print(f"🔗 Link: https://x.com/{post.author_handle}/status/{post.id}")
        print('=' * 70)

    async def _desktop_notification(self, post: PostEvent) -> None:
        """Send desktop notification (macOS support)."""
        try:
            # Create notification message
            title = f"@{post.author_handle}: New Post"
            message = post.content[:100] + ('...' if len(post.content) > 100 else '')

            # Use osascript for macOS notifications
            if os.uname().sysname == 'Darwin':  # macOS
                script = f'''
                display notification "{message}" with title "{title}" sound name "default"
                '''
                process = await asyncio.create_subprocess_exec(
                    'osascript', '-e', script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            else:
                # For Linux, could use notify-send if available
                pass

        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")

    async def _webhook_notification(self, post: PostEvent) -> None:
        """Send notification to webhook."""
        if not self._session:
            logger.error("No aiohttp session available for webhook")
            return

        try:
            # Prepare webhook payload
            payload = {
                'event': 'new_post',
                'timestamp': post.timestamp.isoformat(),
                'post': asdict(post)
            }

            # Send to webhook
            async with self._session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status >= 400:
                    logger.error(f"Webhook failed with status {response.status}")
                else:
                    logger.debug(f"Webhook notification sent for post {post.id}")

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

    async def _log_notification(self, post: PostEvent) -> None:
        """Log notification to file."""
        try:
            # Ensure log directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            # Append to log file (JSONL format)
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event': 'post_intercepted',
                'post': asdict(post)
            }

            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            logger.error(f"Failed to log notification: {e}")

    def get_recent_posts(self, count: Optional[int] = None) -> List[PostEvent]:
        """Get recent posts from buffer."""
        if count is None:
            return list(self.buffer)
        return list(self.buffer[-count:])

    def clear_buffer(self) -> None:
        """Clear the notification buffer."""
        self.buffer.clear()


class NotificationAggregator:
    """Aggregates notifications for batch processing."""

    def __init__(self, handler: NotificationHandler, interval_seconds: int = 60):
        self.handler = handler
        self.interval = interval_seconds
        self.pending_posts: List[PostEvent] = []
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the aggregator."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._aggregate_loop())
        logger.info(f"Started notification aggregator with {self.interval}s interval")

    async def stop(self) -> None:
        """Stop the aggregator."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Process remaining posts
        if self.pending_posts:
            await self._process_batch()

    async def add_post(self, post: PostEvent) -> None:
        """Add a post to the aggregation queue."""
        self.pending_posts.append(post)

    async def _aggregate_loop(self) -> None:
        """Main aggregation loop."""
        while self._running:
            await asyncio.sleep(self.interval)
            if self.pending_posts:
                await self._process_batch()

    async def _process_batch(self) -> None:
        """Process a batch of posts."""
        if not self.pending_posts:
            return

        batch = self.pending_posts.copy()
        self.pending_posts.clear()

        logger.info(f"Processing batch of {len(batch)} posts")

        # Send batch notification
        if len(batch) == 1:
            await self.handler.handle_post(batch[0])
        else:
            await self._send_batch_notification(batch)

    async def _send_batch_notification(self, posts: List[PostEvent]) -> None:
        """Send a batch notification."""
        # Console output
        if self.handler.console_output:
            print(f"\n{'=' * 70}")
            print(f"📢 BATCH: {len(posts)} NEW POSTS DETECTED")
            for i, post in enumerate(posts[:5], 1):  # Show first 5
                print(f"{i}. @{post.author_handle}: {post.content[:50]}...")
            if len(posts) > 5:
                print(f"   ... and {len(posts) - 5} more")
            print('=' * 70)

        # Desktop notification
        if self.handler.desktop_notifications:
            title = f"{len(posts)} New Posts"
            message = f"From: {', '.join(set(p.author_handle for p in posts[:3]))}"
            if len(posts) > 3:
                message += f" and {len(posts) - 3} others"

            if os.uname().sysname == 'Darwin':
                script = f'''
                display notification "{message}" with title "{title}" sound name "default"
                '''
                process = await asyncio.create_subprocess_exec(
                    'osascript', '-e', script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

        # Log all posts
        for post in posts:
            await self.handler._log_notification(post)


class NotificationFilter:
    """Advanced filtering for notifications."""

    def __init__(self):
        self.min_likes = 0
        self.min_retweets = 0
        self.min_replies = 0
        self.require_media = False
        self.exclude_retweets = False
        self.exclude_replies = False
        self.language: Optional[str] = None
        self.verified_only = False

    def should_notify(self, post: PostEvent) -> bool:
        """Check if a post should trigger a notification."""
        # Check metrics thresholds
        if post.likes < self.min_likes:
            return False
        if post.retweets < self.min_retweets:
            return False
        if post.replies < self.min_replies:
            return False

        # Check content requirements
        if self.require_media and not post.has_media:
            return False
        if self.exclude_retweets and post.is_retweet:
            return False
        if self.exclude_replies and post.is_reply:
            return False

        return True