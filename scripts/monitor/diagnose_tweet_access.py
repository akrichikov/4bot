#!/usr/bin/env python3
"""
Diagnostic Script - Capture what's actually shown when accessing tweets
Takes screenshots to see what the bot is seeing
"""

import asyncio
from typing import Any as _Moved
import json
from pathlib import Path
from datetime import datetime
import logging

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('DIAGNOSE')


class TweetAccessDiagnostic:
    """Diagnose why tweets appear unavailable when trying to reply"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"
        self.screenshot_dir = "/Users/doctordre/projects/4bot/Docs/status/diagnostics"

    async def setup_browser(self):
        """Setup browser with authentication"""
        logger.info("🌐 Setting up diagnostic browser...")

        # Create screenshot directory
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)

        # Check authentication
        if Path(self.storage_state_path).exists():
            with open(self.storage_state_path, 'r') as f:
                storage_data = json.load(f)
                cookie_count = len(storage_data.get('cookies', []))
                logger.info(f"✅ Loaded {cookie_count} cookies")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # Run with GUI for diagnostics
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await self.browser.new_context(
            storage_state=self.storage_state_path,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await context.new_page()

        # Navigate to home first
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Take screenshot of home page
        await self.page.screenshot(path=f"{self.screenshot_dir}/00_home.png")
        logger.info(f"📸 Home page screenshot saved")

        # Dismiss any overlays
        try:
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
        except:
            pass

        return True

    async def diagnose_tweet_access(self):
        """Test accessing specific tweets and capture what happens"""

        # Test tweets - mix of ones that should be available
        test_tweets = [
            {"username": "bitcoindata21", "url": "https://x.com/bitcoindata21/status/1976989902295150920"},
            {"username": "CryptoNobler", "url": "https://x.com/CryptoNobler/status/1978742203036921985"},
            {"username": "Cointelegraph", "url": "https://x.com/Cointelegraph/status/1968548337163911538"}
        ]

        for i, tweet_data in enumerate(test_tweets, 1):
            logger.info(f"\n🔍 Testing tweet {i}: @{tweet_data['username']}")
            logger.info(f"   URL: {tweet_data['url']}")

            try:
                # Navigate to tweet
                await self.page.goto(tweet_data['url'], wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Take initial screenshot
                screenshot_path = f"{self.screenshot_dir}/{i:02d}_{tweet_data['username']}_initial.png"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"   📸 Initial screenshot: {screenshot_path}")

                # Check content
                content = await self.page.content()

                # Check for unavailable indicators
                unavailable_indicators = [
                    "doesn't exist",
                    "this tweet is unavailable",
                    "this post is unavailable",
                    "account is suspended",
                    "something went wrong"
                ]

                is_unavailable = any(indicator in content.lower() for indicator in unavailable_indicators)

                if is_unavailable:
                    logger.warning(f"   ❌ Tweet shows as unavailable")
                    # Find which indicator matched
                    for indicator in unavailable_indicators:
                        if indicator in content.lower():
                            logger.warning(f"      Found: '{indicator}'")
                else:
                    logger.info(f"   ✅ Tweet appears available")

                    # Try to find and click reply button
                    try:
                        reply_button = await self.page.wait_for_selector('[data-testid="reply"]', timeout=3000)
                        if reply_button:
                            logger.info(f"   🎯 Reply button found")

                            # Take screenshot before clicking
                            await self.page.screenshot(
                                path=f"{self.screenshot_dir}/{i:02d}_{tweet_data['username']}_before_reply.png"
                            )

                            # Click reply
                            await reply_button.click()
                            await asyncio.sleep(2)

                            # Take screenshot after clicking
                            await self.page.screenshot(
                                path=f"{self.screenshot_dir}/{i:02d}_{tweet_data['username']}_after_reply.png"
                            )
                            logger.info(f"   📸 Reply dialog screenshot saved")

                            # Check if text area appeared
                            text_area = await self.page.query_selector('[data-testid="tweetTextarea_0"]')
                            if text_area:
                                logger.info(f"   ✅ Reply text area is accessible")
                            else:
                                logger.warning(f"   ⚠️ Reply text area not found")

                            # Close reply dialog
                            await self.page.keyboard.press('Escape')
                            await asyncio.sleep(1)

                    except Exception as e:
                        logger.warning(f"   ⚠️ Could not interact with reply: {e}")

                # Check authentication status
                profile_element = await self.page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]')
                if profile_element:
                    logger.info(f"   ✅ Still authenticated")
                else:
                    logger.warning(f"   ⚠️ May not be authenticated")

            except Exception as e:
                logger.error(f"   Error diagnosing tweet: {e}")

            await asyncio.sleep(3)

        logger.info("\n📊 Diagnostic complete. Check screenshots in:")
        logger.info(f"   {self.screenshot_dir}")

    async def run(self):
        """Main diagnostic execution"""
        try:
            if not await self.setup_browser():
                logger.error("Browser setup failed!")
                return

            await self.diagnose_tweet_access()

            logger.info("\n✅ Diagnostic session complete")
            logger.info("Browser will remain open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Diagnostic error: {e}")
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    diagnostic = TweetAccessDiagnostic()
    await diagnostic.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           TWEET ACCESS DIAGNOSTIC TOOL v1.0               ║
    ║                                                           ║
    ║     Capturing what the bot sees when accessing tweets     ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
