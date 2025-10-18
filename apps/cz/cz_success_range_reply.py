#!/usr/bin/env python3
"""
CZ Success Range Reply System - Start from tweet #53 where replies worked
Uses the exact successful pattern from the unified system
"""

import asyncio
import random
import sys
import os
import re
import json
import time
from pathlib import Path
from xbot.profiles import storage_state_path
from typing import List
import logging
from typing import Any as _Moved

try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('CZ_SUCCESS')


class CZSuccessRangeReply:
    """Reply system starting from successful range"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.storage_state_path = str(storage_state_path("4botbsc"))
        self.tweet_file = "Docs/4Bot Tweets.md"
        self.success_count = 0
        self.fail_count = 0
        self.start_index = 52  # Start from tweet #53 (0-indexed)

    def parse_tweet_urls(self) -> List[str]:
        """Extract unique tweet URLs"""
        with open(self.tweet_file, 'r') as f:
            content = f.read()

        # Extract all URLs
        url_pattern = r'https://x\.com/[^/\s]+/status/\d+'
        all_urls = re.findall(url_pattern, content)

        # Deduplicate
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"📋 Found {len(unique_urls)} unique tweet URLs")
        logger.info(f"🎯 Starting from tweet #{self.start_index + 1} (successful range)")
        return unique_urls

    def get_cz_response(self, index: int) -> str:
        """Generate CZ response - use pattern that worked"""
        # These responses worked from tweet #53 onwards
        success_responses = [
            "Skeptics watch. Builders build.",
            "4. BUIDL > FUD",
            "4.",
            "Love to see it! Ship it!",
            "Great question! The answer is simple: We BUIDL.",
            "Keep building! BUIDL.",
            "This is the way.",
            "Long-term vision always wins.",
            "We're building the future.",
            "Stay focused. Keep going."
        ]

        # Mix in some FUD responses for variety
        if random.random() < 0.3:
            return "4"

        return random.choice(success_responses)

    async def setup_browser(self):
        """Setup browser with proper authentication"""
        logger.info("🌐 Initializing browser for success range...")

        # Check authentication
        if Path(self.storage_state_path).exists():
            with open(self.storage_state_path, 'r') as f:
                storage_data = json.load(f)
                cookie_count = len(storage_data.get('cookies', []))
                logger.info(f"✅ Loaded {cookie_count} cookies from profile")
        else:
            logger.error("❌ No authentication found!")
            return False

        # Launch browser
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-setuid-sandbox'
            ]
        )

        # Create context with cookies
        context = await self.browser.new_context(
            storage_state=self.storage_state_path,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await context.new_page()

        # Navigate to home first to establish session
        logger.info("📱 Establishing session...")
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Check if we're logged in
        content = await self.page.content()
        if "@4botbsc" in content or "4botbsc" in content:
            logger.info("✅ Authenticated as @4botbsc")
        else:
            logger.warning("⚠️ May not be properly authenticated")

        logger.info("✅ Browser ready for success range replies")
        return True

    async def reply_with_success_pattern(self, url: str, index: int) -> bool:
        """Reply using the exact pattern that worked from tweet #53"""
        try:
            logger.info(f"🎯 [{index+1}] Processing: {url}")

            # Navigate to tweet
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Dismiss overlay if present (this worked in successful attempts)
            try:
                overlay = await self.page.query_selector('.r-ipm5af')
                if overlay:
                    logger.info("Found overlay, dismissing...")
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(2)
            except:
                pass

            # Check if tweet exists
            content = await self.page.content()
            if "doesn't exist" in content or "unavailable" in content.lower():
                logger.warning("⚠️ Tweet unavailable")
                self.fail_count += 1
                return False

            # Generate response
            response = self.get_cz_response(index)
            logger.info(f"💬 CZ says: {response}")

            # Find and click reply button
            reply_button = await self.page.wait_for_selector('[data-testid="reply"]', timeout=3000)
            if reply_button:
                await reply_button.click()
                await asyncio.sleep(2)

                # Type the reply
                text_area = await self.page.wait_for_selector(
                    '[data-testid="tweetTextarea_0"]',
                    timeout=5000
                )
                await text_area.click()
                await asyncio.sleep(0.5)

                # Type character by character (this worked)
                for char in response:
                    await self.page.keyboard.type(char)
                    await asyncio.sleep(0.01)

                await asyncio.sleep(1)

                # Send using keyboard shortcut (most reliable)
                await self.page.keyboard.press('Control+Enter')
                await asyncio.sleep(3)

                # Check if sent
                new_content = await self.page.content()
                if "Your Tweet was sent" in new_content or len(new_content) > len(content) + 100:
                    self.success_count += 1
                    logger.info(f"✅ Reply #{self.success_count} posted successfully!")
                    return True

            self.fail_count += 1
            logger.warning("❌ Could not post reply")
            return False

        except Exception as e:
            logger.error(f"Error: {e}")
            self.fail_count += 1
            return False

    async def run(self):
        """Main execution - start from successful range"""
        try:
            # Parse URLs
            urls = self.parse_tweet_urls()

            if not urls:
                logger.error("No URLs found!")
                return

            # Skip to successful range
            urls_to_process = urls[self.start_index:]

            logger.info(f"📊 Will process {len(urls_to_process)} tweets (from #{self.start_index + 1} to #{len(urls)})")

            # Setup browser
            if not await self.setup_browser():
                logger.error("Browser setup failed!")
                return

            logger.info("=" * 60)
            logger.info("🚀 CZ SUCCESS RANGE REPLY SYSTEM ACTIVATED")
            logger.info(f"📊 Target: {len(urls_to_process)} tweets")
            logger.info(f"🎯 Starting from tweet #{self.start_index + 1} (proven success range)")
            logger.info("🧠 Mission: Reply to tweets that work")
            logger.info("=" * 60)

            # Process each tweet
            for i, url in enumerate(urls_to_process):
                actual_index = self.start_index + i
                success = await self.reply_with_success_pattern(url, actual_index)

                # Progress update every 10
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 Progress: {i+1}/{len(urls_to_process)}")
                    logger.info(f"✅ Success: {self.success_count} | ❌ Failed: {self.fail_count}")

                # Rate limiting - longer wait for successful posts
                if success:
                    wait = random.randint(7, 10)
                else:
                    wait = random.randint(3, 5)

                if i < len(urls_to_process) - 1:
                    logger.info(f"⏰ Waiting {wait}s...")
                    await asyncio.sleep(wait)

            # Final summary
            logger.info("=" * 60)
            logger.info("🏁 MISSION COMPLETE")
            logger.info(f"📊 Final Results:")
            logger.info(f"   Total tweets: {len(urls_to_process)}")
            logger.info(f"   ✅ Successful: {self.success_count}")
            logger.info(f"   ❌ Failed: {self.fail_count}")
            if len(urls_to_process) > 0:
                success_rate = (self.success_count / len(urls_to_process)) * 100
                logger.info(f"   Success rate: {success_rate:.1f}%")
            logger.info("=" * 60)
            logger.info("💪 CZ has spoken.")
            logger.info("🚀 Back to BUIDLing.")
            logger.info("4.")

        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            if self.browser:
                await self.browser.close()
                logger.info("🛑 Browser closed")


async def main():
    system = CZSuccessRangeReply()
    await system.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          CZ SUCCESS RANGE REPLY SYSTEM v1.0              ║
    ║                                                           ║
    ║      Starting from tweet #53 (proven success range)       ║
    ║         Using exact pattern that worked before            ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print("Initiating in 3 seconds...")
    time.sleep(3)

    asyncio.run(main())
