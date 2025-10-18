#!/usr/bin/env python3
"""
Verify posted tweets by navigating to the profile page
"""

import asyncio
from typing import Any as _Moved
import sys
import os
from pathlib import Path
import logging

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from xbot.cookies import load_cookie_json, merge_into_storage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('verify_posts')


async def verify_posts():
    """Navigate to profile and check for posted tweets"""

    cookies_path = "auth_data/x_cookies.json"
    storage_state_path = "config/profiles/4botbsc/storageState.json"

    # Load cookies
    if Path(cookies_path).exists():
        cookies = load_cookie_json(Path(cookies_path))
        merge_into_storage(
            Path(storage_state_path),
            cookies,
            filter_domains=[".x.com", ".twitter.com"]
        )
        logger.info(f"✅ Loaded {len(cookies)} cookies")

    # Launch browser (not headless so you can see)
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # Set to False to see the browser
        args=['--disable-blink-features=AutomationControlled']
    )

    context = await browser.new_context(
        storage_state=storage_state_path if Path(storage_state_path).exists() else None,
        viewport={"width": 1920, "height": 1080}
    )

    page = await context.new_page()

    # Navigate to the profile page
    logger.info("📱 Navigating to profile page...")
    await page.goto("https://x.com/4botbsc", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    # Check for tweets
    logger.info("🔍 Looking for posted tweets...")
    tweets = await page.query_selector_all('[data-testid="tweet"]')
    logger.info(f"📊 Found {len(tweets)} tweets on profile")

    # Try to extract tweet text
    for i, tweet in enumerate(tweets[:5], 1):  # Check first 5 tweets
        try:
            text_element = await tweet.query_selector('[data-testid="tweetText"]')
            if text_element:
                text = await text_element.inner_text()
                logger.info(f"Tweet {i}: {text[:100]}...")
        except:
            pass

    # Also check the Posts tab explicitly
    posts_tab = await page.query_selector('a[href="/4botbsc"][role="tab"]')
    if posts_tab:
        await posts_tab.click()
        await asyncio.sleep(3)
        logger.info("📍 Clicked on Posts tab")

    # Take a screenshot for verification (repo-relative path)
    screens_dir = ROOT / "artifacts" / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screens_dir / "profile_verification.png"
    await page.screenshot(path=str(screenshot_path), full_page=False)
    logger.info(f"📸 Screenshot saved to {screenshot_path}")

    logger.info("\n🔍 Please check the browser window to see the profile page")
    logger.info("Press Enter to close the browser...")
    input()

    await browser.close()
    logger.info("✅ Verification complete")


if __name__ == "__main__":
    asyncio.run(verify_posts())
