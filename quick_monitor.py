#!/usr/bin/env python3
"""
Quick monitoring script for specific X/Twitter use cases.
Simple examples for common monitoring scenarios.
"""

import asyncio
import json
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import sys

sys.path.insert(0, str(Path(__file__).parent))

from xbot.event_interceptor import EventInterceptor, PostEvent
from xbot.notifications import NotificationHandler


class QuickMonitor:
    """Simplified monitor for quick deployment."""

    def __init__(self, config_file='monitor_config.json'):
        self.config = self.load_config(config_file)
        self.interceptor = EventInterceptor()
        self.posts_collected = []
        self.browser = None
        self.page = None

    def load_config(self, config_file):
        """Load configuration from file."""
        with open(config_file, 'r') as f:
            return json.load(f)

    async def monitor_keywords(self, keywords, duration_minutes=5):
        """Monitor specific keywords for a set duration."""
        print(f"\n🔍 Monitoring keywords: {', '.join(keywords)}")
        print(f"⏱️  Duration: {duration_minutes} minutes\n")

        # Create notification handler
        handler = NotificationHandler({
            'console_output': True,
            'desktop_notifications': True,
            'log_file': f'keyword_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        })

        # Setup callback for keyword matches
        async def keyword_callback(post: PostEvent):
            content_lower = post.content.lower()
            matched_keywords = [kw for kw in keywords if kw.lower() in content_lower]
            if matched_keywords:
                print(f"\n✅ MATCH: {', '.join(matched_keywords)}")
                print(f"👤 @{post.author_handle}")
                print(f"💬 {post.content[:200]}...")
                print(f"📊 ❤️ {post.likes} 🔄 {post.retweets}")
                self.posts_collected.append(post)
                await handler.handle_post(post)

        self.interceptor.add_callback(keyword_callback)

        # Start monitoring
        async with handler:
            await self._run_monitor(duration_minutes * 60)

        return self.posts_collected

    async def monitor_author(self, author_handle, duration_minutes=5):
        """Monitor a specific author's posts."""
        print(f"\n👤 Monitoring author: @{author_handle}")
        print(f"⏱️  Duration: {duration_minutes} minutes\n")

        handler = NotificationHandler({
            'console_output': True,
            'desktop_notifications': True,
            'log_file': f'author_{author_handle}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        })

        async def author_callback(post: PostEvent):
            if post.author_handle.lower() == author_handle.lower():
                print(f"\n✅ NEW POST from @{author_handle}")
                print(f"💬 {post.content}")
                print(f"📊 ❤️ {post.likes} 🔄 {post.retweets} 💬 {post.replies}")
                if post.has_media:
                    print(f"📷 Contains {len(post.media_urls)} media items")
                self.posts_collected.append(post)
                await handler.handle_post(post)

        self.interceptor.add_callback(author_callback)

        async with handler:
            await self._run_monitor(duration_minutes * 60)

        return self.posts_collected

    async def monitor_trending(self, min_engagement=100, duration_minutes=5):
        """Monitor trending posts based on engagement metrics."""
        print(f"\n📈 Monitoring trending posts")
        print(f"🎯 Minimum engagement: {min_engagement} (likes + retweets)")
        print(f"⏱️  Duration: {duration_minutes} minutes\n")

        handler = NotificationHandler({
            'console_output': True,
            'desktop_notifications': True,
            'log_file': f'trending_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        })

        async def trending_callback(post: PostEvent):
            engagement = post.likes + post.retweets
            if engagement >= min_engagement:
                print(f"\n🔥 TRENDING POST")
                print(f"👤 @{post.author_handle}")
                print(f"💬 {post.content[:200]}...")
                print(f"📊 Total engagement: {engagement} (❤️ {post.likes} + 🔄 {post.retweets})")
                self.posts_collected.append(post)
                await handler.handle_post(post)

        self.interceptor.add_callback(trending_callback)

        async with handler:
            await self._run_monitor(duration_minutes * 60)

        return self.posts_collected

    async def collect_sample_posts(self, count=10):
        """Collect a sample of posts for analysis."""
        print(f"\n📦 Collecting {count} sample posts...")

        collected = []

        async def collect_callback(post: PostEvent):
            if len(collected) < count:
                collected.append(post)
                print(f"  [{len(collected)}/{count}] @{post.author_handle}: {post.content[:50]}...")

        self.interceptor.add_callback(collect_callback)

        # Monitor until we have enough posts
        await self._run_monitor(max_duration=300, stop_condition=lambda: len(collected) >= count)

        # Save to file
        output_file = f'sample_posts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(
                [self._post_to_dict(p) for p in collected],
                f,
                indent=2,
                default=str
            )

        print(f"\n✅ Saved {len(collected)} posts to {output_file}")
        return collected

    def _post_to_dict(self, post: PostEvent):
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

    async def _run_monitor(self, max_duration=300, stop_condition=None):
        """Run the monitor for specified duration or until condition met."""
        playwright = await async_playwright().start()

        try:
            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=self.config['browser']['headless'],
                args=['--disable-blink-features=AutomationControlled']
            )

            # Create context
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            # Load cookies
            cookie_file = Path('auth_data/x_cookies.json')
            if cookie_file.exists():
                cookies = json.loads(cookie_file.read_text())
                await context.add_cookies(cookies)

            # Create page and navigate
            self.page = await context.new_page()
            await self.page.goto('https://x.com/home', wait_until='networkidle')
            await self.page.wait_for_selector('article', timeout=30000)

            # Start monitoring
            await self.interceptor.start_monitoring(self.page)

            # Monitor loop
            start_time = asyncio.get_event_loop().time()
            scroll_interval = self.config['browser']['scroll_interval']
            last_scroll = start_time

            while True:
                current_time = asyncio.get_event_loop().time()

                # Check stop conditions
                if stop_condition and stop_condition():
                    break
                if current_time - start_time > max_duration:
                    break

                # Scroll periodically
                if current_time - last_scroll > scroll_interval:
                    await self.page.evaluate(f"window.scrollBy(0, {self.config['browser']['scroll_amount']})")
                    last_scroll = current_time

                await asyncio.sleep(1)

        finally:
            if self.page:
                await self.interceptor.stop_monitoring(self.page)
            if self.browser:
                await self.browser.close()
            await playwright.stop()


async def main():
    """Main entry point with examples."""
    monitor = QuickMonitor()

    if len(sys.argv) < 2:
        print("""
Usage: python quick_monitor.py <command> [options]

Commands:
  keywords <word1> <word2> ...  - Monitor specific keywords
  author <handle>                - Monitor specific author
  trending [min_engagement]     - Monitor trending posts
  sample [count]                 - Collect sample posts

Examples:
  python quick_monitor.py keywords AI crypto bitcoin
  python quick_monitor.py author elonmusk
  python quick_monitor.py trending 500
  python quick_monitor.py sample 20
        """)
        return

    command = sys.argv[1]

    if command == "keywords" and len(sys.argv) > 2:
        keywords = sys.argv[2:]
        posts = await monitor.monitor_keywords(keywords, duration_minutes=5)
        print(f"\n📊 Collected {len(posts)} matching posts")

    elif command == "author" and len(sys.argv) > 2:
        author = sys.argv[2].replace('@', '')
        posts = await monitor.monitor_author(author, duration_minutes=5)
        print(f"\n📊 Collected {len(posts)} posts from @{author}")

    elif command == "trending":
        min_engagement = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        posts = await monitor.monitor_trending(min_engagement, duration_minutes=5)
        print(f"\n📊 Collected {len(posts)} trending posts")

    elif command == "sample":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        posts = await monitor.collect_sample_posts(count)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())