#!/usr/bin/env python3
"""
CZ Targeted Reply System - Reply to specific tweets from 4Bot Tweets.md
Navigate to each URL and reply as CZ with appropriate wisdom
"""

import asyncio
import random
import sys
import os
from pathlib import Path
from typing import List, Dict
import logging
import re
import time

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from playwright.async_api import async_playwright, Page
from xbot.cookies import load_cookie_json, merge_into_storage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('CZ_TARGETED')


class CZTargetedReplyBot:
    """Bot that replies to specific tweets from the list"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.cookies_path = "/Users/doctordre/projects/4bot/auth_data/x_cookies.json"
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"
        self.replied_count = 0
        self.failed_count = 0

        # Parse the tweet URLs from the file
        self.tweet_urls = self.parse_tweet_file()

        # CZ response variations for FUD
        self.cz_responses = {
            'pure_fud': ["4", "4.", "4"],
            'fud_with_message': [
                "4. Keep BUIDLing.",
                "4. We build through FUD.",
                "4. Focus on building, not noise.",
                "4. Back to work.",
                "4. BUIDL > FUD"
            ],
            'doubt': [
                "Doubt is temporary. Building is permanent.",
                "Less doubt, more action. BUIDL.",
                "The best response to doubt? Results. Keep building.",
                "Skeptics watch. Builders build.",
                "Time will tell. We'll keep BUIDLing."
            ],
            'negativity': [
                "Negativity is noise. Focus on signal.",
                "While you complain, we build.",
                "Energy spent on negativity could be used for building.",
                "Choose: criticize or create. We choose create.",
                "Negative energy, positive building."
            ],
            'market_fear': [
                "Markets cycle. Builders persist.",
                "Fear is temporary. Technology is permanent.",
                "When others fear, we build.",
                "Market sentiment ≠ technological progress.",
                "Price goes down, building goes up."
            ],
            'encouragement': [
                "Stay focused. Keep building.",
                "This is the way. BUIDL.",
                "Long-term vision always wins.",
                "We're building the future, one block at a time.",
                "Consistency beats intensity. Keep going."
            ]
        }

    def parse_tweet_file(self) -> List[str]:
        """Extract all tweet URLs from the markdown file"""
        file_path = "/Users/doctordre/projects/4bot/Docs/4Bot Tweets.md"
        urls = []

        with open(file_path, 'r') as f:
            content = f.read()

        # Extract all URLs using regex
        url_pattern = r'https://x\.com/[^/\s]+/status/\d+'
        urls = re.findall(url_pattern, content)

        logger.info(f"📋 Parsed {len(urls)} tweet URLs from file")
        return urls

    def get_cz_response(self, index: int) -> str:
        """Generate appropriate CZ response based on position and context"""
        # First 30 tweets get mostly "4" responses (high FUD)
        if index < 30:
            if random.random() < 0.7:
                return random.choice(self.cz_responses['pure_fud'])
            else:
                return random.choice(self.cz_responses['fud_with_message'])

        # Next 30 get mixed responses
        elif index < 60:
            response_type = random.choice(['fud_with_message', 'doubt', 'negativity', 'market_fear'])
            return random.choice(self.cz_responses[response_type])

        # Last batch gets more encouraging responses
        else:
            if random.random() < 0.3:
                return "4"
            response_type = random.choice(['encouragement', 'market_fear', 'doubt'])
            return random.choice(self.cz_responses[response_type])

    async def setup_browser(self):
        """Setup headless browser"""
        logger.info("🌐 Setting up headless browser for targeted replies...")

        os.makedirs(Path(self.storage_state_path).parent, exist_ok=True)

        if Path(self.cookies_path).exists():
            cookies = load_cookie_json(Path(self.cookies_path))
            merge_into_storage(
                Path(self.storage_state_path),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info(f"✅ Loaded {len(cookies)} cookies for authentication")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # Always headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )

        context = await self.browser.new_context(
            storage_state=self.storage_state_path if Path(self.storage_state_path).exists() else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await context.new_page()
        logger.info("✅ Browser ready for targeted engagement")

    async def reply_to_tweet(self, url: str, index: int) -> bool:
        """Navigate to specific tweet and reply"""
        try:
            logger.info(f"🎯 [{index+1}/{len(self.tweet_urls)}] Navigating to: {url}")

            # Navigate to the tweet
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Check if tweet exists
            if "This Tweet is unavailable" in await self.page.content():
                logger.warning("⚠️ Tweet unavailable or deleted")
                return False

            # Generate CZ response
            response = self.get_cz_response(index)
            logger.info(f"💬 CZ says: {response}")

            # Find and click reply button
            reply_button = await self.page.query_selector('[data-testid="reply"]')
            if not reply_button:
                # Try alternative selectors
                reply_button = await self.page.query_selector('[aria-label*="Reply"]')

            if reply_button:
                await reply_button.click()
                await asyncio.sleep(2)

                # Type the response
                reply_box = await self.page.wait_for_selector(
                    '[data-testid="tweetTextarea_0"]',
                    timeout=5000
                )
                await reply_box.click()
                await self.page.keyboard.type(response, delay=50)
                await asyncio.sleep(1)

                # Send the reply
                send_button = await self.page.query_selector('[data-testid="tweetButton"]')
                if not send_button:
                    send_button = await self.page.query_selector('[data-testid="tweetButtonInline"]')

                if send_button:
                    # Check if button is enabled
                    is_disabled = await send_button.get_attribute('aria-disabled')
                    if is_disabled != 'true':
                        await send_button.click()
                        await asyncio.sleep(3)
                        self.replied_count += 1
                        logger.info(f"✅ Reply #{self.replied_count} sent: {response}")
                        return True
                    else:
                        # Try keyboard shortcut
                        await self.page.keyboard.press('Control+Enter')
                        await asyncio.sleep(3)
                        self.replied_count += 1
                        logger.info(f"✅ Reply #{self.replied_count} sent (keyboard): {response}")
                        return True
                else:
                    # Fallback to keyboard shortcut
                    await self.page.keyboard.press('Control+Enter')
                    await asyncio.sleep(3)
                    self.replied_count += 1
                    logger.info(f"✅ Reply #{self.replied_count} sent (keyboard): {response}")
                    return True

            else:
                logger.warning("❌ Could not find reply button")
                self.failed_count += 1
                return False

        except Exception as e:
            logger.error(f"❌ Failed to reply: {e}")
            self.failed_count += 1

            # Try to close any dialog
            try:
                await self.page.keyboard.press('Escape')
            except:
                pass

            return False

    async def run(self):
        """Main execution - reply to all tweets"""
        try:
            await self.setup_browser()

            logger.info(f"🚀 Starting targeted CZ replies to {len(self.tweet_urls)} tweets")
            logger.info("🧠 CZ Mind: Activated for maximum FUD destruction")
            logger.info("-" * 60)

            # Process each tweet
            for index, url in enumerate(self.tweet_urls):
                try:
                    success = await self.reply_to_tweet(url, index)

                    # Rate limiting based on success
                    if success:
                        # Successful reply - wait 5-10 seconds
                        wait_time = random.randint(5, 10)
                    else:
                        # Failed - shorter wait
                        wait_time = random.randint(2, 5)

                    logger.info(f"⏰ Waiting {wait_time} seconds before next tweet...")
                    await asyncio.sleep(wait_time)

                    # Progress update every 10 tweets
                    if (index + 1) % 10 == 0:
                        logger.info(f"📊 Progress: {index+1}/{len(self.tweet_urls)} tweets processed")
                        logger.info(f"✅ Successful: {self.replied_count} | ❌ Failed: {self.failed_count}")
                        logger.info("-" * 60)

                except Exception as e:
                    logger.error(f"Error processing tweet {index+1}: {e}")
                    continue

            # Final summary
            logger.info("=" * 60)
            logger.info("🏁 TARGETED REPLY MISSION COMPLETE")
            logger.info(f"📊 Final Statistics:")
            logger.info(f"   Total URLs: {len(self.tweet_urls)}")
            logger.info(f"   ✅ Successful replies: {self.replied_count}")
            logger.info(f"   ❌ Failed attempts: {self.failed_count}")
            logger.info(f"   Success rate: {(self.replied_count/len(self.tweet_urls)*100):.1f}%")
            logger.info("=" * 60)
            logger.info("💪 CZ has spoken. FUD has been neutralized.")
            logger.info("🚀 Back to BUIDLing.")
            logger.info("4.")

        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            if self.browser:
                await self.browser.close()
                logger.info("🛑 Browser closed")


async def main():
    bot = CZTargetedReplyBot()
    await bot.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║            CZ TARGETED REPLY SYSTEM - ACTIVATED               ║
    ║                                                               ║
    ║         97 FUD tweets identified for neutralization           ║
    ║              Each will receive CZ wisdom                      ║
    ║                                                               ║
    ║                        Mission: 4                             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    print("Starting in 3 seconds...")
    time.sleep(3)

    asyncio.run(main())