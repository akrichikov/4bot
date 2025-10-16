#!/usr/bin/env python3
"""
Diagnostic script to debug why posts aren't being detected.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def diagnose():
    """Run diagnostics on the monitoring system."""

    print("🔍 MONITORING DIAGNOSTICS")
    print("=" * 70)

    # Load cookies
    cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
    with open(cookie_file, 'r') as f:
        cookies = json.load(f)

    print(f"✅ Loaded {len(cookies)} cookies")

    # Check for critical cookies
    critical = ['auth_token', 'ct0', 'twid']
    for name in critical:
        cookie = next((c for c in cookies if c['name'] == name), None)
        if cookie:
            print(f"✅ {name}: {cookie['value'][:20]}...")
        else:
            print(f"❌ {name}: NOT FOUND")

    playwright = await async_playwright().start()

    try:
        # Launch browser with UI for debugging
        print("\n🌐 Launching browser (visible for debugging)...")
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )

        await context.add_cookies(cookies)
        page = await context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"📝 Console: {msg.text}"))

        print("\n📍 Navigating to X.com...")
        await page.goto('https://x.com', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Check if logged in
        print("\n🔍 Checking login status...")

        # Check URL
        current_url = page.url
        print(f"Current URL: {current_url}")

        if "login" in current_url or "i/flow" in current_url:
            print("❌ Redirected to login - NOT LOGGED IN")
        else:
            print("✅ Not on login page")

        # Navigate to home
        print("\n📍 Going to home feed...")
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Check for articles
        print("\n🔍 Checking for posts (article elements)...")
        articles = await page.query_selector_all('article')
        print(f"Found {len(articles)} article elements")

        if articles:
            print("\n📊 Analyzing first post structure...")
            first_article = articles[0]

            # Check for expected elements
            checks = [
                ('User info', '[data-testid="User-Name"]'),
                ('Tweet text', '[data-testid="tweetText"]'),
                ('Reply button', '[data-testid="reply"]'),
                ('Retweet button', '[data-testid="retweet"]'),
                ('Like button', '[data-testid="like"],[data-testid="unlike"]'),
                ('Status link', 'a[href*="/status/"]')
            ]

            for name, selector in checks:
                element = await first_article.query_selector(selector)
                if element:
                    print(f"  ✅ {name}: Found")
                else:
                    print(f"  ❌ {name}: NOT FOUND")

        # Test the observer script
        print("\n🔍 Testing DOM observer injection...")

        observer_test = """
        (() => {
            console.log('[TEST] Injecting observer...');

            // Test finding articles
            const articles = document.querySelectorAll('article');
            console.log(`[TEST] Found ${articles.length} articles on page`);

            if (articles.length > 0) {
                // Try to extract data from first article
                const article = articles[0];

                const link = article.querySelector('a[href*="/status/"]');
                if (link) {
                    console.log('[TEST] Found status link:', link.href);
                } else {
                    console.log('[TEST] No status link found');
                }

                const userElement = article.querySelector('[data-testid="User-Name"]');
                if (userElement) {
                    console.log('[TEST] Found user element');
                } else {
                    console.log('[TEST] No user element found');
                }

                const tweetText = article.querySelector('[data-testid="tweetText"]');
                if (tweetText) {
                    console.log('[TEST] Found tweet text:', tweetText.textContent.substring(0, 50));
                } else {
                    console.log('[TEST] No tweet text found');
                }
            }

            // Test mutation observer
            const observer = new MutationObserver((mutations) => {
                console.log(`[TEST] Mutation detected: ${mutations.length} mutations`);
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            console.log('[TEST] Observer active');

            // Trigger a test mutation
            setTimeout(() => {
                const testDiv = document.createElement('div');
                testDiv.id = 'test-mutation';
                document.body.appendChild(testDiv);
                document.body.removeChild(testDiv);
            }, 1000);

            return 'Observer test complete';
        })();
        """

        result = await page.evaluate(observer_test)
        print(f"Observer test result: {result}")

        # Wait for console messages
        await asyncio.sleep(3)

        print("\n" + "=" * 70)
        print("🔍 DIAGNOSTICS COMPLETE")
        print("\nBrowser will stay open for 10 seconds for inspection...")
        print("Check the browser to see if you're logged in")
        print("=" * 70)

        await asyncio.sleep(10)

        await browser.close()

    finally:
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(diagnose())