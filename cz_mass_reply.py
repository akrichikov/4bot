#!/usr/bin/env python3
"""
CZ Mass Reply System - Reply to all non-4botbsc posts as CZ
Full headless autonomous engagement
"""

import asyncio
import random
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging
import re

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from playwright.async_api import async_playwright, Page
from xbot.cookies import load_cookie_json, merge_into_storage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('CZ_MASS_REPLY')


class CZReplyEngine:
    """The CZ consciousness that replies to everything"""

    def __init__(self):
        self.replied_to = set()  # Track what we've already replied to
        self.reply_count = 0

    def generate_reply(self, post_text: str, author: str) -> str:
        """Generate CZ-style reply based on post content"""
        text_lower = post_text.lower()

        # FUD Detection - immediate "4"
        fud_indicators = [
            'scam', 'rug', 'dump', 'crash', 'ponzi', 'fraud', 'fake',
            'dead', 'over', 'failed', 'exit', 'hack', 'steal'
        ]
        if any(word in text_lower for word in fud_indicators):
            if random.random() < 0.8:
                return "4"
            else:
                return "4. We BUIDL through FUD."

        # Price/Moon talk
        if any(word in text_lower for word in ['price', 'moon', 'pump', 'dump', 'chart']):
            responses = [
                "Focus on building, not charts. BUIDL.",
                "Price is temporary. Technology is permanent.",
                "Less chart watching, more building.",
                "Markets move. Builders build. Keep BUIDLing.",
                "Zoom out. We're building the future here."
            ]
            return random.choice(responses)

        # Building/Development
        if any(word in text_lower for word in ['build', 'ship', 'launch', 'deploy', 'code']):
            responses = [
                "This is the way! Keep BUIDLing 🚀",
                "Love to see it! Ship it!",
                "Builders gonna build. LFG!",
                "That's what I'm talking about. BUIDL!",
                "Yes! More building, less talking."
            ]
            return random.choice(responses)

        # Questions
        if '?' in post_text:
            if 'when' in text_lower:
                return "The best time is now. Stop waiting, start BUIDLing."
            elif 'how' in text_lower:
                return "Start small. Learn fast. Build consistently. The path reveals itself."
            elif 'why' in text_lower:
                return "Because we're building the future of finance. That's why."
            elif 'what' in text_lower:
                return "Focus on real utility and ethical teams. BUIDL what matters."
            else:
                return "Great question. The answer is always: keep BUIDLing."

        # Regulatory/Government
        if any(word in text_lower for word in ['sec', 'regulation', 'government', 'legal']):
            return "Clear regulations help the industry mature. We work with regulators globally."

        # Security concerns
        if any(word in text_lower for word in ['safe', 'security', 'protect', 'hack']):
            return "User protection first. Always. Funds are #SAFU."

        # Success/Achievement posts
        if any(word in text_lower for word in ['success', 'achieved', 'milestone', 'launched']):
            responses = [
                "Congratulations! Keep shipping!",
                "This is just the beginning. Keep BUIDLing!",
                "Well done! Now build the next thing.",
                "Love to see the progress. Don't stop now!",
            ]
            return random.choice(responses)

        # Negative sentiment
        if any(word in text_lower for word in ['sad', 'lost', 'down', 'bear', 'worried']):
            responses = [
                "Stay strong. We BUIDL through everything.",
                "Tough times don't last. Builders do.",
                "Focus on what you can control. Keep building.",
                "This too shall pass. Keep your head up and BUIDL.",
                "Bear markets are for builders. This is our time."
            ]
            return random.choice(responses)

        # Default encouraging responses
        default_responses = [
            "Keep pushing forward. BUIDL.",
            "Focus on the long game.",
            "Less noise, more signal.",
            "We're all gonna make it. Keep building.",
            "Stay focused on what matters.",
            "The future rewards the builders.",
            "Long-term thinking always wins.",
            "BUIDL through everything.",
            "Winners focus on winning.",
            "This is the way.",
            "Consistency is key. Keep going.",
            "Every day we're building the future."
        ]

        return random.choice(default_responses)


class CZMassReplyBot:
    """Bot that replies to all non-4botbsc posts"""

    def __init__(self):
        self.engine = CZReplyEngine()
        self.browser = None
        self.page = None
        self.cookies_path = "/Users/doctordre/projects/4bot/auth_data/x_cookies.json"
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"

    async def setup_browser(self):
        """Setup headless browser"""
        logger.info("🌐 Setting up headless browser...")

        os.makedirs(Path(self.storage_state_path).parent, exist_ok=True)

        if Path(self.cookies_path).exists():
            cookies = load_cookie_json(Path(self.cookies_path))
            merge_into_storage(
                Path(self.storage_state_path),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info(f"✅ Loaded {len(cookies)} cookies")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        context = await self.browser.new_context(
            storage_state=self.storage_state_path if Path(self.storage_state_path).exists() else None,
            viewport={"width": 1920, "height": 1080}
        )

        self.page = await context.new_page()
        logger.info("✅ Browser ready")

    async def reply_to_post(self, post_element, author: str, text: str, post_id: str) -> bool:
        """Reply to a specific post"""
        try:
            # Generate CZ reply
            reply_text = self.engine.generate_reply(text, author)
            logger.info(f"💬 Replying to @{author}: {reply_text[:50]}...")

            # Click reply button
            reply_button = await post_element.query_selector('[data-testid="reply"]')
            if not reply_button:
                reply_button = await post_element.query_selector('[aria-label*="Reply"]')

            if reply_button:
                await reply_button.click()
                await asyncio.sleep(2)

                # Type reply
                reply_box = await self.page.wait_for_selector(
                    '[data-testid="tweetTextarea_0"]',
                    timeout=5000
                )
                await reply_box.click()
                await self.page.keyboard.type(reply_text, delay=50)
                await asyncio.sleep(1)

                # Send reply
                await self.page.keyboard.press('Control+Enter')
                await asyncio.sleep(3)

                self.engine.reply_count += 1
                logger.info(f"✅ Reply #{self.engine.reply_count} sent: {reply_text}")
                return True

        except Exception as e:
            logger.error(f"Failed to reply: {e}")
            # Try to close any dialog
            try:
                await self.page.keyboard.press('Escape')
            except:
                pass
        return False

    async def scan_timeline(self):
        """Scan timeline for posts to reply to"""
        logger.info("📱 Scanning timeline...")

        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Scroll to load posts
        for _ in range(3):
            await self.page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

        # Find all posts
        posts = await self.page.query_selector_all('[data-testid="tweet"]')
        logger.info(f"Found {len(posts)} posts to process")

        for post in posts:
            try:
                # Get author
                author_element = await post.query_selector('a[role="link"][href^="/"] span')
                if not author_element:
                    continue

                author = await author_element.inner_text()

                # Skip our own posts
                if '4bot' in author.lower() or '4bot' in (await post.inner_text()).lower():
                    continue

                # Get post text
                text_element = await post.query_selector('[data-testid="tweetText"]')
                if not text_element:
                    continue

                text = await text_element.inner_text()

                # Generate unique ID
                post_id = f"{author}_{text[:20]}"

                # Skip if already replied
                if post_id in self.engine.replied_to:
                    continue

                # Reply to this post
                await self.reply_to_post(post, author, text, post_id)
                self.engine.replied_to.add(post_id)

                # Rate limit
                await asyncio.sleep(random.randint(5, 10))

            except Exception as e:
                logger.debug(f"Error processing post: {e}")

    async def scan_notifications(self):
        """Scan and reply to all notifications/mentions"""
        logger.info("🔔 Scanning notifications...")

        await self.page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Get all notification items
        notifications = await self.page.query_selector_all('[data-testid="cellInnerDiv"]')
        logger.info(f"Found {len(notifications)} notifications")

        for notif in notifications:
            try:
                # Extract text
                text_element = await notif.query_selector('[data-testid="tweetText"]')
                if not text_element:
                    continue

                text = await text_element.inner_text()

                # Get author
                author_link = await notif.query_selector('a[role="link"][href^="/"]')
                if not author_link:
                    continue

                author = (await author_link.get_attribute('href')).strip('/')

                # Skip our own
                if '4bot' in author.lower():
                    continue

                # Generate reply
                reply_text = self.engine.generate_reply(text, author)

                # Click reply
                reply_btn = await notif.query_selector('[data-testid="reply"]')
                if reply_btn:
                    await reply_btn.click()
                    await asyncio.sleep(2)

                    # Type and send
                    reply_box = await self.page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
                    await reply_box.type(reply_text, delay=50)
                    await self.page.keyboard.press('Control+Enter')
                    await asyncio.sleep(3)

                    self.engine.reply_count += 1
                    logger.info(f"✅ Replied to @{author}: {reply_text}")

                # Rate limit
                await asyncio.sleep(random.randint(5, 10))

            except Exception as e:
                logger.debug(f"Error with notification: {e}")

    async def search_and_reply(self, search_terms: List[str]):
        """Search for specific terms and reply"""
        for term in search_terms:
            logger.info(f"🔍 Searching for: {term}")

            # Navigate to search
            search_url = f"https://x.com/search?q={term}&src=typed_query&f=live"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Process search results
            posts = await self.page.query_selector_all('[data-testid="tweet"]')
            logger.info(f"Found {len(posts)} posts about {term}")

            for post in posts[:10]:  # Limit to 10 per search
                try:
                    # Similar processing as timeline
                    text_element = await post.query_selector('[data-testid="tweetText"]')
                    if not text_element:
                        continue

                    text = await text_element.inner_text()

                    # Skip 4bot posts
                    if '4bot' in text.lower():
                        continue

                    # Get author
                    author_element = await post.query_selector('span:has-text("@")')
                    author = await author_element.inner_text() if author_element else "user"

                    await self.reply_to_post(post, author, text, f"{term}_{text[:20]}")
                    await asyncio.sleep(random.randint(5, 10))

                except Exception as e:
                    logger.debug(f"Error with search result: {e}")

    async def run(self):
        """Main execution"""
        try:
            await self.setup_browser()

            logger.info("🚀 CZ Mass Reply System Active")
            logger.info("🧠 Scanning for posts to enlighten with BUIDL wisdom...")

            # 1. Reply to timeline posts
            await self.scan_timeline()

            # 2. Reply to all notifications
            await self.scan_notifications()

            # 3. Search for crypto topics and reply
            crypto_terms = [
                "crypto", "bitcoin", "ethereum", "blockchain", "defi",
                "web3", "nft", "buidl", "hodl", "bear market"
            ]
            await self.search_and_reply(crypto_terms)

            logger.info(f"✅ Mass reply complete! Total replies sent: {self.engine.reply_count}")
            logger.info("🧠 CZ wisdom has been spread across the timeline")
            logger.info("4. Back to BUIDLing.")

        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    bot = CZMassReplyBot()
    await bot.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           CZ MASS REPLY SYSTEM - ACTIVATED            ║
    ║                                                        ║
    ║     Spreading BUIDL wisdom across the timeline        ║
    ║           Every FUD gets a 4                          ║
    ║         Every builder gets encouragement              ║
    ║                                                        ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())