#!/usr/bin/env python3
"""
Safe monitoring test using akrichikov@gmail.com test account.
This prevents any accidental posts or interactions on production accounts.
"""

import asyncio
from typing import Any as _Moved
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

from xbot.event_interceptor import EventInterceptor, PostEvent, create_keyword_subscription
from xbot.notifications import NotificationHandler
from chrome_profiles.profile_mapper import ChromeProfileManager


class SafeMonitorTest:
    """Safe monitoring test with account verification."""

    def __init__(self):
        self.manager = ChromeProfileManager()
        self.interceptor = EventInterceptor()
        self.test_profile = None
        self.cookie_file = None
        self.posts_detected = []

    def verify_test_account(self) -> bool:
        """Verify we're using a test account, not production."""
        # Get the Default profile (akrichikov@gmail.com)
        if "Default" not in self.manager.profiles:
            print("❌ Default profile not found")
            return False

        self.test_profile = self.manager.profiles["Default"]

        # Safety check - ensure it's not marked as production
        if self.test_profile.is_production:
            print(f"⚠️ SAFETY: Profile {self.test_profile.profile_name} is marked as PRODUCTION")
            print("Aborting to prevent accidental production use")
            return False

        # Verify it's the expected test account
        if self.test_profile.email != "akrichikov@gmail.com":
            print(f"⚠️ Unexpected email: {self.test_profile.email}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return False

        self.cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        if not self.cookie_file.exists():
            print(f"❌ Cookie file not found: {self.cookie_file}")
            return False

        print("✅ Safety checks passed:")
        print(f"   Profile: {self.test_profile.profile_name}")
        print(f"   Email: {self.test_profile.email}")
        print(f"   X Handle: @{self.test_profile.x_handle}")
        print(f"   Status: TEST ACCOUNT (safe for monitoring)")

        return True

    async def test_monitor(self, duration_seconds=60):
        """Run a safe monitoring test."""
        if not self.verify_test_account():
            print("❌ Safety verification failed. Exiting.")
            return

        print(f"\n🚀 Starting safe monitoring test for {duration_seconds} seconds...")
        print("=" * 70)

        # Load cookies
        with open(self.cookie_file, 'r') as f:
            cookies = json.load(f)

        # Setup notification handler (console only for testing)
        notification_config = {
            'console_output': True,
            'desktop_notifications': False,  # Disabled for testing
            'log_file': f'test_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        }
        handler = NotificationHandler(notification_config)

        # Create a simple callback to track posts
        async def post_callback(post: PostEvent):
            self.posts_detected.append(post)
            print(f"\n🔍 POST DETECTED #{len(self.posts_detected)}")
            print(f"   Author: @{post.author_handle}")
            print(f"   Content: {post.content[:100]}..." if len(post.content) > 100 else f"   Content: {post.content}")
            print(f"   Engagement: ❤️ {post.likes} 🔄 {post.retweets} 💬 {post.replies}")
            await handler.handle_post(post)

        # Add callback
        self.interceptor.add_callback(post_callback)

        # Add a test keyword subscription
        test_subscription = create_keyword_subscription(
            name="Test Keywords",
            keywords=["tech", "AI", "news", "breaking"],  # Common words for testing
            callback=lambda post: print(f"  ⭐ Keyword match in post from @{post.author_handle}")
        )
        self.interceptor.add_subscription(test_subscription)

        playwright = await async_playwright().start()

        try:
            # Launch browser (visible for testing)
            print("\n🌐 Launching browser...")
            browser = await playwright.chromium.launch(
                headless=False,  # Show browser for verification
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ]
            )

            # Create context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            # Add cookies
            print("🍪 Adding cookies...")
            await context.add_cookies(cookies)

            # Create page
            page = await context.new_page()

            # Navigate to X
            print("📍 Navigating to X.com...")
            await page.goto('https://x.com/home', wait_until='networkidle')

            # Wait for feed
            try:
                await page.wait_for_selector('article', timeout=30000)
                print("✅ Feed loaded successfully")

                # Verify we're on the right account by checking the page
                try:
                    # Try to find account identifier on the page
                    account_elem = await page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
                    if account_elem:
                        href = await account_elem.get_attribute('href')
                        print(f"🔍 Logged in as: {href}")
                except:
                    pass

            except:
                print("⚠️ Feed did not load - might not be logged in")

            # Start monitoring
            async with handler:
                await self.interceptor.start_monitoring(page)
                print("\n📡 Monitoring active! Watching for new posts...")
                print("   (Scroll in the browser to load more posts)")
                print(f"   Monitoring for {duration_seconds} seconds...")
                print("=" * 70)

                # Monitor for specified duration
                start_time = asyncio.get_event_loop().time()
                scroll_count = 0

                while asyncio.get_event_loop().time() - start_time < duration_seconds:
                    # Auto-scroll every 10 seconds
                    if int(asyncio.get_event_loop().time() - start_time) % 10 == 0 and scroll_count < 5:
                        await page.evaluate("window.scrollBy(0, 300)")
                        scroll_count += 1
                        print(f"   📜 Auto-scrolled ({scroll_count}/5)")

                    await asyncio.sleep(1)

                print("\n⏱️ Monitoring period ended")

            # Stop monitoring
            await self.interceptor.stop_monitoring(page)

            # Summary
            print("\n" + "=" * 70)
            print("📊 MONITORING SUMMARY")
            print("=" * 70)
            print(f"Total posts detected: {len(self.posts_detected)}")

            if self.posts_detected:
                print("\nTop authors:")
                from collections import Counter
                authors = Counter(p.author_handle for p in self.posts_detected)
                for author, count in authors.most_common(5):
                    print(f"  @{author}: {count} posts")

                print("\nEngagement stats:")
                total_likes = sum(p.likes for p in self.posts_detected)
                total_retweets = sum(p.retweets for p in self.posts_detected)
                print(f"  Total likes seen: {total_likes}")
                print(f"  Total retweets seen: {total_retweets}")

            # Close browser
            await browser.close()

        finally:
            await playwright.stop()

        print("\n✅ Test completed safely")
        return self.posts_detected


async def main():
    """Run the safe monitoring test."""
    monitor = SafeMonitorTest()

    # Run a 30-second test by default
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    posts = await monitor.test_monitor(duration_seconds=duration)

    if posts:
        # Save results
        output_file = f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump([{
                'id': p.id,
                'author': p.author_handle,
                'content': p.content[:200],
                'likes': p.likes,
                'retweets': p.retweets
            } for p in posts], f, indent=2)
        print(f"\n📁 Results saved to: {output_file}")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     Safe X/Twitter Monitoring Test               ║
    ║     Account: akrichikov@gmail.com (TEST)         ║
    ╠══════════════════════════════════════════════════╣
    ║  This test uses a non-production account to      ║
    ║  safely test the monitoring system.              ║
    ║                                                  ║
    ║  Usage: python test_monitor_safe.py [duration]   ║
    ║  Default duration: 30 seconds                    ║
    ╚══════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
