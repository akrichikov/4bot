#!/usr/bin/env python3
"""
Simplified monitoring test - focuses on core functionality.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

from xbot.event_interceptor import EventInterceptor, PostEvent


async def simple_test():
    """Simple monitoring test with better error handling."""

    print("🚀 Starting simplified monitoring test...")
    print("=" * 70)

    # Load test account cookies
    cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
    if not cookie_file.exists():
        print(f"❌ Cookie file not found: {cookie_file}")
        return

    with open(cookie_file, 'r') as f:
        cookies = json.load(f)

    print(f"🍪 Loaded {len(cookies)} cookies from test account")

    interceptor = EventInterceptor()
    posts_detected = []

    # Simple callback to track posts
    async def post_callback(post: PostEvent):
        posts_detected.append(post)
        print(f"\n✅ POST #{len(posts_detected)} DETECTED!")
        print(f"   Author: @{post.author_handle} ({post.author})")
        print(f"   Content: {post.content[:150]}...")
        print(f"   Stats: ❤️ {post.likes} 🔄 {post.retweets} 💬 {post.replies}")
        if post.has_media:
            print(f"   Media: {len(post.media_urls)} items")

    interceptor.add_callback(post_callback)

    playwright = await async_playwright().start()

    try:
        # Launch browser with visible window
        print("\n🌐 Launching browser (visible for debugging)...")
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Create context
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Add cookies
        print("🍪 Adding cookies to browser context...")
        await context.add_cookies(cookies)

        # Create page
        page = await context.new_page()

        # Navigate with better error handling
        print("📍 Navigating to X.com...")
        try:
            # First go to x.com root to establish cookies
            await page.goto('https://x.com', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)

            # Then navigate to home
            print("📍 Navigating to home feed...")
            await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=15000)

        except Exception as e:
            print(f"⚠️ Navigation warning: {e}")
            print("Continuing anyway...")

        # Wait a bit for page to stabilize
        await asyncio.sleep(3)

        # Check if we have articles (posts)
        try:
            articles = await page.query_selector_all('article')
            print(f"📊 Found {len(articles)} posts on initial load")

            if len(articles) == 0:
                print("⚠️ No posts found - may not be logged in")
                print("Opening browser for manual inspection...")

                # Take a screenshot for debugging
                screenshot_path = f"debug_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")

        except Exception as e:
            print(f"⚠️ Could not check for articles: {e}")

        # Start monitoring
        print("\n📡 Starting event monitoring...")
        await interceptor.start_monitoring(page)

        print("✅ Monitoring active! Watching for new posts...")
        print("   (The browser will stay open for 20 seconds)")
        print("   (Try scrolling manually to load new posts)")
        print("=" * 70)

        # Monitor for 20 seconds
        for i in range(20):
            await asyncio.sleep(1)
            if i % 5 == 0 and i > 0:
                # Auto-scroll every 5 seconds
                await page.evaluate("window.scrollBy(0, 200)")
                print(f"   📜 Auto-scrolled at {i} seconds...")

        print("\n⏹️ Stopping monitoring...")
        await interceptor.stop_monitoring(page)

        # Results
        print("\n" + "=" * 70)
        print(f"📊 RESULTS: Detected {len(posts_detected)} posts")

        if posts_detected:
            print("\nSample posts:")
            for i, post in enumerate(posts_detected[:3], 1):
                print(f"\n{i}. @{post.author_handle}: {post.content[:100]}...")

        print("\n✅ Test completed!")

        # Keep browser open for inspection
        print("\n🔍 Browser will stay open for 5 more seconds for inspection...")
        await asyncio.sleep(5)

        await browser.close()

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()

    return posts_detected


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     Simplified X/Twitter Monitoring Test         ║
    ║     Using: akrichikov@gmail.com (test account)   ║
    ╚══════════════════════════════════════════════════╝
    """)

    posts = asyncio.run(simple_test())

    if posts:
        print(f"\n💾 Saving {len(posts)} posts to results file...")
        with open(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump([{
                'id': p.id,
                'author': p.author_handle,
                'content': p.content[:200],
                'timestamp': p.timestamp.isoformat()
            } for p in posts], f, indent=2)