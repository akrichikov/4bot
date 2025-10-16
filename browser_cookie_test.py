#!/usr/bin/env python3
"""
Test browser with cookies and keep it open for inspection/manual login.
"""

import asyncio
import json
from pathlib import Path
import pytest
from playwright.async_api import async_playwright

# Skip this module during automated test runs; intended for manual, interactive use.
if __name__ != "__main__":
    pytest.skip(
        "Interactive browser test skipped by default. Run this file directly to execute.",
        allow_module_level=True,
    )


async def test_browser_cookies():
    """Open browser with cookies and keep it open."""

    print("🌐 Browser Cookie Test")
    print("=" * 70)

    # Check for cookie file
    cookie_file = Path("chrome_profiles/cookies/default_cookies.json")

    if cookie_file.exists():
        print(f"✅ Found cookie file: {cookie_file}")
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        print(f"🍪 Loaded {len(cookies)} cookies")

        # Check for auth cookies
        auth_cookies = [c for c in cookies if c['name'] in ['auth_token', 'ct0', 'twid']]
        print(f"\n🔑 Authentication cookies found:")
        for c in auth_cookies:
            print(f"   - {c['name']}: {c['value'][:20]}...")
    else:
        print(f"❌ No cookie file found at {cookie_file}")
        cookies = []

    playwright = await async_playwright().start()

    try:
        # Launch browser with UI
        print("\n🚀 Launching browser (will stay open)...")
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox'
            ]
        )

        # Create context
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US'
        )

        if cookies:
            print("🍪 Adding cookies to browser...")
            await context.add_cookies(cookies)

        # Create page
        page = await context.new_page()

        print("\n📍 Navigating to X.com...")
        try:
            # Go to X.com
            response = await page.goto('https://x.com', wait_until='domcontentloaded', timeout=30000)
            print(f"   Response status: {response.status if response else 'No response'}")

            # Wait a bit
            await asyncio.sleep(3)

            # Check current URL
            current_url = page.url
            print(f"   Current URL: {current_url}")

            # Check if we're logged in by looking for specific elements
            await asyncio.sleep(2)

            # Try to find indicators of being logged in
            is_logged_in = False

            # Check for home timeline
            try:
                home_link = await page.query_selector('[data-testid="AppTabBar_Home_Link"]')
                if home_link:
                    print("✅ Found home link - appears to be logged in")
                    is_logged_in = True
            except:
                pass

            # Check for compose tweet button
            try:
                compose = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                if compose:
                    print("✅ Found compose button - appears to be logged in")
                    is_logged_in = True
            except:
                pass

            # Check for login prompt
            try:
                login_button = await page.query_selector('[data-testid="LoginForm_Login_Button"]')
                if login_button:
                    print("⚠️ Found login button - NOT logged in")
                    is_logged_in = False
            except:
                pass

            if not is_logged_in:
                print("\n⚠️ Does not appear to be logged in")
                print("📝 You may need to:")
                print("   1. Log in manually in the browser")
                print("   2. After logging in, we'll extract fresh cookies")

            else:
                print("\n✅ Appears to be logged in!")
                print("🔄 Navigating to home feed...")
                await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=15000)

                # Count posts
                await asyncio.sleep(3)
                articles = await page.query_selector_all('article')
                print(f"📊 Found {len(articles)} posts in feed")

        except Exception as e:
            print(f"❌ Navigation error: {e}")

        print("\n" + "=" * 70)
        print("🔍 BROWSER WILL STAY OPEN")
        print("You can:")
        print("  1. Check if you're logged in")
        print("  2. Log in manually if needed")
        print("  3. Navigate around to test")
        print("  4. Press Ctrl+C when done")
        print("=" * 70)

        # Keep browser open
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ Closing browser...")

    finally:
        if 'browser' in locals():
            await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_browser_cookies())
    except KeyboardInterrupt:
        print("\n✅ Test completed")
