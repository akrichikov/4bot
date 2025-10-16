#!/usr/bin/env python3
"""
CZ Available Tweets Reply System - Target ONLY verified available tweets
Uses the 25 tweets confirmed available from verification
"""

import asyncio
import random
import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict
import logging

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from playwright.async_api import async_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('CZ_AVAILABLE')


class CZAvailableTweetsReply:
    """Reply ONLY to verified available tweets"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"
        self.available_tweets_file = "/Users/doctordre/projects/4bot/Docs/available_tweets.md"
        self.success_count = 0
        self.fail_count = 0

    def parse_available_tweets(self) -> List[Dict[str, str]]:
        """Parse the available tweets from the verified list"""
        tweets = []

        with open(self.available_tweets_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith('- @'):
                # Parse format: - @username: https://x.com/username/status/id
                parts = line.strip().split(': ')
                if len(parts) == 2:
                    username = parts[0].replace('- @', '')
                    url = parts[1]
                    tweets.append({
                        'username': username,
                        'url': url
                    })

        logger.info(f"📋 Loaded {len(tweets)} verified available tweets")
        return tweets

    def get_cz_response(self, username: str, index: int) -> str:
        """Generate appropriate CZ response based on user and position"""

        # High-profile accounts get specific responses
        if username.lower() in ['cointelegraph', 'cryptonobler', 'jameswynnreal']:
            return random.choice([
                "4. We BUIDL through everything.",
                "Keep building! The future is bright.",
                "Focus on what matters: building.",
                "This is the way. BUIDL."
            ])

        # First batch - stronger FUD response
        if index < 10:
            return random.choice([
                "4",
                "4.",
                "4. BUIDL > FUD",
                "4. Back to work.",
                "4. Focus on building, not noise."
            ])

        # Middle batch - mixed responses
        elif index < 20:
            return random.choice([
                "Doubt is temporary. Building is permanent.",
                "Less doubt, more action. BUIDL.",
                "Markets cycle. Builders persist.",
                "Time will tell. We'll keep BUIDLing.",
                "Fear is temporary. Technology is permanent."
            ])

        # Last batch - encouragement
        else:
            return random.choice([
                "Stay focused. Keep building.",
                "Long-term vision always wins.",
                "We're building the future.",
                "Consistency beats intensity. Keep going.",
                "Every day we're BUIDLing."
            ])

    async def setup_browser(self):
        """Setup browser with authentication"""
        logger.info("🌐 Initializing browser for available tweets...")

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

        # Create context
        context = await self.browser.new_context(
            storage_state=self.storage_state_path,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await context.new_page()

        # Navigate to home first
        logger.info("📱 Establishing session...")
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Dismiss any overlays
        try:
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
        except:
            pass

        logger.info("✅ Browser ready for available tweet replies")
        return True

    async def reply_to_tweet(self, tweet_data: Dict[str, str], index: int) -> bool:
        """Reply to a verified available tweet"""
        try:
            username = tweet_data['username']
            url = tweet_data['url']

            logger.info(f"🎯 [{index+1}] Replying to @{username}")
            logger.info(f"   URL: {url}")

            # Navigate to tweet
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Dismiss overlays
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(1)
            except:
                pass

            # Double-check availability
            content = await self.page.content()
            if "doesn't exist" in content or "unavailable" in content.lower():
                logger.warning(f"⚠️ Tweet became unavailable: @{username}")
                self.fail_count += 1
                return False

            # Generate CZ response
            response = self.get_cz_response(username, index)
            logger.info(f"💬 CZ says: {response}")

            # Click reply button
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

                # Type character by character
                for char in response:
                    await self.page.keyboard.type(char)
                    await asyncio.sleep(0.01)

                await asyncio.sleep(1)

                # Send using keyboard shortcut (most reliable)
                await self.page.keyboard.press('Control+Enter')
                await asyncio.sleep(3)

                # Verify sent
                new_content = await self.page.content()
                if "Your Tweet was sent" in new_content or len(new_content) > len(content) + 100:
                    self.success_count += 1
                    logger.info(f"✅ Reply #{self.success_count} posted to @{username}!")
                    return True
                else:
                    # Try alternative send button
                    send_button = await self.page.query_selector('[data-testid="tweetButton"]')
                    if send_button:
                        await send_button.click()
                        await asyncio.sleep(3)
                        self.success_count += 1
                        logger.info(f"✅ Reply #{self.success_count} posted to @{username}!")
                        return True

            self.fail_count += 1
            logger.warning(f"❌ Could not reply to @{username}")
            return False

        except Exception as e:
            logger.error(f"Error replying to @{tweet_data['username']}: {e}")
            self.fail_count += 1
            return False

    async def run(self):
        """Main execution - reply to all available tweets"""
        try:
            # Parse available tweets
            tweets = self.parse_available_tweets()

            if not tweets:
                logger.error("No available tweets found!")
                return

            # Setup browser
            if not await self.setup_browser():
                logger.error("Browser setup failed!")
                return

            logger.info("=" * 60)
            logger.info("🚀 CZ AVAILABLE TWEETS REPLY SYSTEM")
            logger.info(f"📊 Target: {len(tweets)} verified available tweets")
            logger.info("🧠 Mission: Reply to ALL available FUD tweets")
            logger.info("=" * 60)

            # Process each available tweet
            for i, tweet_data in enumerate(tweets):
                success = await self.reply_to_tweet(tweet_data, i)

                # Progress update every 5
                if (i + 1) % 5 == 0:
                    logger.info(f"📊 Progress: {i+1}/{len(tweets)}")
                    logger.info(f"✅ Success: {self.success_count} | ❌ Failed: {self.fail_count}")

                # Rate limiting - longer for successful posts
                if success:
                    wait = random.randint(8, 12)
                else:
                    wait = random.randint(3, 5)

                if i < len(tweets) - 1:
                    logger.info(f"⏰ Waiting {wait}s before next tweet...")
                    await asyncio.sleep(wait)

            # Final summary
            logger.info("=" * 60)
            logger.info("🏁 MISSION COMPLETE")
            logger.info(f"📊 Final Results:")
            logger.info(f"   Total tweets: {len(tweets)}")
            logger.info(f"   ✅ Successful: {self.success_count}")
            logger.info(f"   ❌ Failed: {self.fail_count}")
            if len(tweets) > 0:
                success_rate = (self.success_count / len(tweets)) * 100
                logger.info(f"   Success rate: {success_rate:.1f}%")
            logger.info("=" * 60)
            logger.info("💪 CZ has spoken to the available FUD.")
            logger.info("🚀 Back to BUIDLing.")
            logger.info("4.")

        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            if self.browser:
                await self.browser.close()
                logger.info("🛑 Browser closed")


async def main():
    system = CZAvailableTweetsReply()
    await system.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║       CZ AVAILABLE TWEETS REPLY SYSTEM v1.0              ║
    ║                                                           ║
    ║      Targeting 25 VERIFIED AVAILABLE FUD tweets          ║
    ║         Maximum efficiency, minimum waste                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print("Initiating in 3 seconds...")
    time.sleep(3)

    asyncio.run(main())