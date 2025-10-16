#!/usr/bin/env python3
"""
Post a test message to X/Twitter from the test account.
This will be intercepted by the headless monitor.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import random


async def post_test_message():
    """Post an AI-related message from test account."""

    print("🐦 X/Twitter Test Poster")
    print("=" * 70)

    # AI-related test messages
    test_messages = [
        f"🤖 Testing AI monitoring system at {datetime.now().strftime('%H:%M:%S')} - This is an automated test post for ML pipeline verification #{random.randint(1000, 9999)}",
        f"🧠 Neural network test: GPT-based monitoring active. Timestamp: {datetime.now().isoformat()} #AI #Testing",
        f"📊 Machine learning test post: Real-time event interception working! Test ID: {random.randint(1000, 9999)} #AITesting",
        f"🔬 AI experiment: Testing LLM-powered post detection. Random seed: {random.randint(1000, 9999)}",
        f"💡 Artificial intelligence monitoring test active. Deep learning pipeline operational. #{random.randint(1000, 9999)}"
    ]

    message = random.choice(test_messages)
    print(f"Message to post: {message}")

    # Load cookies
    cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
    with open(cookie_file, 'r') as f:
        cookies = json.load(f)

    print(f"✅ Loaded {len(cookies)} cookies")

    playwright = await async_playwright().start()

    try:
        # Launch browser VISIBLY so we can see what's happening
        print("\n🌐 Launching visible browser...")
        browser = await playwright.chromium.launch(
            headless=False,  # VISIBLE browser
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        await context.add_cookies(cookies)
        page = await context.new_page()

        # Navigate to X
        print("📍 Navigating to X.com...")
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Check if we're logged in
        articles = await page.query_selector_all('article')
        print(f"✅ Feed loaded with {len(articles)} posts")

        # Find the compose tweet button/area
        print("\n📝 Looking for compose area...")

        # Try different selectors for the compose area
        compose_selectors = [
            '[data-testid="tweetTextarea_0"]',  # Main compose box
            '[data-testid="SideNav_NewTweet_Button"]',  # New tweet button
            '[aria-label="Compose post"]',
            '[aria-label="Tweet"]',
            'div[role="textbox"]'
        ]

        compose_element = None
        for selector in compose_selectors:
            compose_element = await page.query_selector(selector)
            if compose_element:
                print(f"✅ Found compose element: {selector}")
                break

        if not compose_element:
            # Try clicking the compose button first
            print("🔍 Looking for compose button...")
            compose_button = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
            if compose_button:
                print("✅ Clicking compose button...")
                await compose_button.click()
                await asyncio.sleep(2)

                # Now look for the text area
                compose_element = await page.query_selector('[data-testid="tweetTextarea_0"]')

        if compose_element:
            print("✅ Compose area ready")

            # Click on the compose area to focus
            await compose_element.click()
            await asyncio.sleep(1)

            # Type the message
            print(f"⌨️ Typing message...")
            await page.keyboard.type(message, delay=50)  # Type with slight delay for realism
            await asyncio.sleep(2)

            # Find and click the Tweet/Post button
            print("🔍 Looking for post button...")
            post_button_selectors = [
                '[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButton"]',
                'button[aria-label="Post"]',
                'button:has-text("Post")',
                'button:has-text("Tweet")'
            ]

            post_button = None
            for selector in post_button_selectors:
                post_button = await page.query_selector(selector)
                if post_button:
                    print(f"✅ Found post button: {selector}")
                    break

            if post_button:
                # Check if button is enabled
                is_disabled = await post_button.get_attribute('disabled')
                if not is_disabled:
                    print("🚀 Clicking post button...")
                    await post_button.click()
                    await asyncio.sleep(3)

                    print("✅ POST SUBMITTED!")
                    print("=" * 70)
                    print("The headless monitor should intercept this post!")
                    print("Check the monitor logs for the intercepted AI post")
                    print("=" * 70)

                    # Keep browser open for verification
                    print("\n🔍 Browser will stay open for 10 seconds for verification...")
                    await asyncio.sleep(10)
                else:
                    print("⚠️ Post button is disabled")
            else:
                print("❌ Could not find post button")
        else:
            print("❌ Could not find compose area")
            print("You may need to manually compose the tweet")
            print("\n📝 Manual instructions:")
            print(f"1. Click on 'What's happening?' or compose button")
            print(f"2. Type: {message}")
            print(f"3. Click Post/Tweet")
            print("\n⏳ Keeping browser open for 30 seconds for manual posting...")
            await asyncio.sleep(30)

        await browser.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     X/Twitter Test Post Creator                  ║
    ║     Account: akrichikov@gmail.com                ║
    ╠══════════════════════════════════════════════════╣
    ║  This will post an AI-related test message       ║
    ║  that should be intercepted by the monitor       ║
    ╚══════════════════════════════════════════════════╝
    """)

    asyncio.run(post_test_message())