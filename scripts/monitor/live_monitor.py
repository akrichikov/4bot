#!/usr/bin/env python3
"""
Live monitoring that prints posts as they're intercepted in real-time.
Shows live feed of X/Twitter posts being detected.
"""

import asyncio
from typing import Any as _Moved
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

from xbot.event_interceptor import EventInterceptor, PostEvent


class LiveMonitor:
    """Live monitoring with real-time output."""

    def __init__(self):
        self.interceptor = EventInterceptor()
        self.post_count = 0
        self.start_time = None

    async def live_post_handler(self, post: PostEvent):
        """Handle posts as they arrive - print immediately."""
        self.post_count += 1
        elapsed = int((asyncio.get_event_loop().time() - self.start_time))

        # Print live post with formatting
        print(f"\n{'=' * 70}")
        print(f"🔴 LIVE POST #{self.post_count} | Time: +{elapsed}s")
        print(f"{'=' * 70}")
        print(f"👤 Author: @{post.author_handle}")
        print(f"📝 Name: {post.author}")
        print(f"💬 Content:")

        # Word wrap content for readability
        content = post.content
        while len(content) > 65:
            print(f"   {content[:65]}")
            content = content[65:]
        if content:
            print(f"   {content}")

        print(f"📊 Engagement: ❤️ {post.likes} | 🔄 {post.retweets} | 💬 {post.replies}")

        if post.has_media:
            print(f"📷 Media: {len(post.media_urls)} item(s)")

        if post.is_retweet:
            print(f"🔄 This is a retweet")

        if post.is_reply:
            print(f"↩️ This is a reply")

        print(f"🔗 Link: https://x.com/{post.author_handle}/status/{post.id}")
        print(f"{'=' * 70}")

    async def run_live_monitor(self, duration_seconds=60):
        """Run live monitoring for specified duration."""
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                   LIVE X/TWITTER MONITOR                         ║
║                                                                  ║
║  Posts will appear here as they are detected in real-time       ║
║  Using test account: akrichikov@gmail.com                       ║
╚══════════════════════════════════════════════════════════════════╝
        """)

        # Load cookies - use the fixed test account cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        if not cookie_file.exists():
            print(f"❌ Cookie file not found: {cookie_file}")
            return

        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        print(f"🍪 Loaded {len(cookies)} cookies")
        print(f"⏱️ Monitoring for {duration_seconds} seconds")
        print(f"🔄 Posts will appear below as they're detected...\n")

        # Add callback for live handling
        self.interceptor.add_callback(self.live_post_handler)

        playwright = await async_playwright().start()

        try:
            # Launch browser (headless for cleaner output)
            browser = await playwright.chromium.launch(
                headless=True,  # Run headless for cleaner console output
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            # Add cookies
            await context.add_cookies(cookies)

            # Create page
            page = await context.new_page()

            # Navigate
            print("🌐 Connecting to X.com...")
            try:
                await page.goto('https://x.com', wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)
                await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=15000)
                print("✅ Connected! Monitoring started...")
                print("📡 Waiting for posts...\n")
            except Exception as e:
                print(f"⚠️ Navigation warning (continuing): {e[:100]}...")

            # Start monitoring
            self.start_time = asyncio.get_event_loop().time()
            await self.interceptor.start_monitoring(page)

            # Initial check for existing posts
            await asyncio.sleep(2)
            articles = await page.query_selector_all('article')
            print(f"📊 Initial scan: {len(articles)} posts on page")
            print(f"🔄 Scrolling to trigger new posts...\n")

            # Monitor and scroll periodically
            for i in range(duration_seconds):
                await asyncio.sleep(1)

                # Progress indicator every 10 seconds
                if i % 10 == 0 and i > 0:
                    print(f"⏱️ [{i}/{duration_seconds}s] Still monitoring... {self.post_count} posts detected so far")

                # Scroll every 5 seconds to load new posts
                if i % 5 == 0:
                    await page.evaluate("window.scrollBy(0, 500)")

            # Stop monitoring
            await self.interceptor.stop_monitoring(page)
            await browser.close()

            # Final summary
            print(f"\n{'=' * 70}")
            print(f"📊 MONITORING COMPLETE")
            print(f"{'=' * 70}")
            print(f"✅ Total posts intercepted: {self.post_count}")
            print(f"⏱️ Duration: {duration_seconds} seconds")
            print(f"📈 Rate: {self.post_count / duration_seconds:.2f} posts/second")
            print(f"{'=' * 70}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()

        return self.post_count


async def main():
    """Main entry point."""
    # Get duration from command line or use default
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    monitor = LiveMonitor()
    posts = await monitor.run_live_monitor(duration_seconds=duration)

    if posts == 0:
        print("\n⚠️ No posts were detected. Possible issues:")
        print("  - Cookies may be expired (try logging in manually)")
        print("  - X.com may have changed their HTML structure")
        print("  - Network connection issues")


if __name__ == "__main__":
    print("Usage: python live_monitor.py [duration_in_seconds]")
    print("Default: 30 seconds\n")

    asyncio.run(main())
