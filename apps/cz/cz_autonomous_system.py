#!/usr/bin/env python3
"""
CZ Autonomous System - Full Headless In-Memory Operation
Operating from https://4bot.fun/ as the embodiment of CZ
"""

import asyncio
import random
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from typing import Any as _Moved
import json
import time

# Add xbot to path
try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright, Page, Browser
from xbot.cookies import load_cookie_json, merge_into_storage
from xbot.vterm import VTerm
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger('CZ')


class CZMind:
    """The consciousness of CZ - generates authentic responses"""

    def __init__(self):
        self.core_beliefs = [
            "Stay Calm and Build",
            "Play the Long Game",
            "Do the Right Thing",
            "See Both Sides",
            "Keep It Simple",
            "Own It",
            "Think Abundance"
        ]

        self.last_4_time = None  # Track when we last responded with "4"

    def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate CZ response based on context"""
        text = context.get('text', '').lower()
        author = context.get('author', 'friend')
        response_type = context.get('type', 'reply')

        # Check for FUD, negativity, or attacks
        fud_words = ['scam', 'rug', 'crash', 'dead', 'fake', 'fraud', 'ponzi', 'dump']
        if any(word in text for word in fud_words):
            # Sometimes just respond with "4", sometimes add a BUIDL message
            if random.random() < 0.7:
                return "4"
            else:
                return "4. Back to BUIDLing."

        # Check for questions about market/price
        if 'price' in text or 'moon' in text or 'pump' in text:
            responses = [
                "Less noise, more signal. Focus on building.",
                "Price is temporary. Technology is permanent. BUIDL.",
                "Markets go up and down. We build through all of them.",
                "Stop watching charts. Start building value.",
            ]
            return random.choice(responses)

        # Check for building/development mentions
        if any(word in text for word in ['build', 'develop', 'create', 'launch', 'ship']):
            responses = [
                "This is the way! Keep BUIDLing 🚀",
                "Exactly right. BUIDL through everything.",
                "Love to see it! Ship code, ignore noise.",
                "Winners focus on winning. Keep building!",
                "That's what separates the real from the noise. BUIDL.",
            ]
            return random.choice(responses)

        # Check for regulatory topics
        if any(word in text for word in ['regulation', 'sec', 'government', 'compliance']):
            return "Clear regulations are good for the industry. We work with regulators globally. Compliance is a core value."

        # Check for security concerns
        if any(word in text for word in ['hack', 'safe', 'security', 'protect']):
            return "User protection is everything. Funds are #SAFU. Security first, always."

        # Educational questions
        if '?' in text:
            if 'how' in text:
                return "Start small, learn constantly, build consistently. The path becomes clear when you begin walking."
            elif 'when' in text:
                return "The best time was yesterday, the next best time is today. Focus on building value, not timing markets."
            elif 'what' in text:
                return "Focus on projects with real utility and ethical teams. Long-term value beats short-term hype."
            else:
                return "Great question! The answer lies in continuous building and long-term thinking."

        # Default encouraging responses
        encouraging = [
            "Keep building! Every day we're creating the future.",
            "Stay focused on what matters. BUIDL.",
            "The future is bright for those who build.",
            "Long-term vision always wins.",
            "Less complaining, more building.",
            "Luck is built over time, consistently.",
            "Focus on signal, not noise.",
            "We're still early. Keep BUIDLing.",
            "This is just the beginning. BUIDL through it all.",
            "Resilience is forged in challenges. Keep going.",
        ]

        return random.choice(encouraging)

    def generate_original_tweet(self) -> str:
        """Generate an original CZ-style tweet"""
        tweet_templates = [
            # Core philosophy
            "Markets are temporary. Technology is permanent. Focus on what matters. #BUIDL",
            "In crypto winter or summer, we BUIDL. That's what separates the real from the noise.",
            "User protection isn't just a feature - it's the foundation. Everything else builds on trust. #SAFU",
            "The best time to plant a tree was 20 years ago. The second best time is now. Same with BUIDLing.",
            "When everyone's panicking, we're shipping code. When everyone's euphoric, we're still shipping code.",
            "Decentralization isn't just technology. It's a mindset shift. Power to the users.",
            "Bear markets are for builders. Bull markets are for builders too. Just BUIDL.",
            "Playing the long game means thinking in decades, not days. The future is being built right now.",
            "Simplicity is the ultimate sophistication. Complex problems, simple solutions.",
            "Every crisis is an opportunity to get stronger. We've been through many. Still here. Still building.",

            # Motivational
            "Winners focus on winning. Losers focus on winners. Stay focused.",
            "Stop complaining, start building. The future rewards the builders.",
            "Your results are your responsibility. Own it.",
            "Less noise, more signal. Cut the distractions.",
            "The loudest voices often have the least to say. Focus on the builders, not the talkers.",

            # Market wisdom
            "Big money is built slowly with stamina. Quick money is usually quick losses.",
            "99.9% of projects will fail. Focus on the 0.1% building real utility.",
            "Price charts are a distraction. Technology charts show the real progress.",
            "A rising tide lifts all boats. We're all in this together.",
            "Zoom out. We're building the financial system of the future.",

            # Innovation
            "True innovation doesn't ask permission. It creates new possibilities.",
            "Blockchain is inevitable, like the internet was. We're just getting started.",
            "AI is a post-blockchain technology. The convergence will be powerful.",
            "Infrastructure today, mainstream tomorrow. Keep laying the foundation.",
            "The future of finance is being written in code. Line by line. Block by block.",

            # Community
            "Community is our moat. Technology can be copied. Culture cannot.",
            "We're not competitors, we're all pioneers in the same revolution.",
            "Education is the key to adoption. Teach, don't preach.",
            "Real value creation takes a community. We BUIDL together.",

            # The iconic one
            "4"
        ]

        return random.choice(tweet_templates)


class CZAutonomousSystem:
    """The complete autonomous CZ system - fully headless, in-memory"""

    def __init__(self):
        self.mind = CZMind()
        self.browser = None
        self.page = None
        self.reply_page = None
        self.vterm = VTerm()
        self.rabbitmq = RabbitMQManager()
        self.running = True
        self.tweets_posted = 0
        self.replies_sent = 0
        self.last_tweet_time = None
        self.cookies_path = "auth_data/x_cookies.json"
        self.storage_state_path = "config/profiles/4botbsc/storageState.json"

        logger.info("🤖 CZ Autonomous System Initializing...")
        logger.info("📍 Operating from: https://4bot.fun/")
        logger.info("🧠 CZ Mind: Active")

    async def setup_browser(self):
        """Setup completely headless browser"""
        logger.info("🌐 Initializing headless browser environment...")

        # Ensure directories exist
        os.makedirs(Path(self.storage_state_path).parent, exist_ok=True)

        # Load cookies
        if Path(self.cookies_path).exists():
            cookies = load_cookie_json(Path(self.cookies_path))
            merge_into_storage(
                Path(self.storage_state_path),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info(f"✅ Authentication loaded: {len(cookies)} cookies")

        # Launch completely headless
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # ALWAYS headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # Create context
        context = await self.browser.new_context(
            storage_state=self.storage_state_path if Path(self.storage_state_path).exists() else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        # Create pages for different operations
        self.page = await context.new_page()  # For posting
        self.reply_page = await context.new_page()  # For replying

        # Navigate both to X.com
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        await self.reply_page.goto("https://x.com/notifications", wait_until="domcontentloaded", timeout=60000)

        logger.info("✅ Headless environment ready")
        logger.info("🧠 CZ consciousness loaded")

    async def post_original_thought(self):
        """Post an original CZ thought"""
        try:
            thought = self.mind.generate_original_tweet()
            logger.info(f"💭 CZ thinks: {thought[:50]}...")

            # Navigate to home
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Click compose
            compose = await self.page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
            if compose:
                await compose.click()
            else:
                await self.page.keyboard.press('n')

            await asyncio.sleep(2)

            # Find text box
            text_box = await self.page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
            await text_box.click()
            await self.page.keyboard.type(thought, delay=50)

            # Post it
            await self.page.keyboard.press('Control+Enter')
            await asyncio.sleep(3)

            self.tweets_posted += 1
            logger.info(f"✅ Posted thought #{self.tweets_posted}: {thought[:50]}...")

        except Exception as e:
            logger.error(f"Failed to post thought: {e}")

    async def monitor_and_respond(self):
        """Monitor notifications and respond as CZ"""
        try:
            # Check notifications page
            await self.reply_page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Look for mentions
            notifications = await self.reply_page.query_selector_all('[data-testid="cellInnerDiv"]')

            for notif in notifications[:5]:  # Process recent ones
                try:
                    # Extract text
                    text_element = await notif.query_selector('[data-testid="tweetText"]')
                    if text_element:
                        text = await text_element.inner_text()

                        # Generate CZ response
                        response = self.mind.generate_response({
                            'text': text,
                            'type': 'mention'
                        })

                        # Click reply button
                        reply_btn = await notif.query_selector('[data-testid="reply"]')
                        if reply_btn:
                            await reply_btn.click()
                            await asyncio.sleep(2)

                            # Type response
                            reply_box = await self.reply_page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
                            await reply_box.type(response, delay=50)

                            # Send
                            await self.reply_page.keyboard.press('Control+Enter')
                            await asyncio.sleep(3)

                            self.replies_sent += 1
                            logger.info(f"↩️ CZ replied #{self.replies_sent}: {response[:50]}...")

                except Exception as e:
                    logger.debug(f"Could not process notification: {e}")

        except Exception as e:
            logger.error(f"Monitor error: {e}")

    async def autonomous_loop(self):
        """Main autonomous operation loop"""
        logger.info("🚀 CZ Autonomous System Active")
        logger.info("🌍 Operating from https://4bot.fun/")

        post_interval = 0

        while self.running:
            try:
                current_time = datetime.now()

                # Post original thoughts every 5-10 minutes
                if not self.last_tweet_time or (current_time - self.last_tweet_time).seconds > random.randint(300, 600):
                    await self.post_original_thought()
                    self.last_tweet_time = current_time

                # Check and respond to mentions every 2 minutes
                if post_interval % 4 == 0:
                    await self.monitor_and_respond()

                # Status update every 10 cycles
                if post_interval % 20 == 0:
                    logger.info(f"📊 Status: {self.tweets_posted} thoughts shared, {self.replies_sent} responses sent")
                    logger.info("🧠 CZ Mind: Active and BUIDLing")

                post_interval += 1
                await asyncio.sleep(30)  # 30 second cycle

            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(60)

    async def run(self):
        """Initialize and run the full autonomous system"""
        try:
            # Start VTerm for command execution
            self.vterm.start()
            logger.info("🖥️ Virtual Terminal: Active")

            # Setup browser
            await self.setup_browser()

            # Start RabbitMQ
            self.rabbitmq.connect()
            logger.info("📡 Message Queue: Connected")

            # Begin autonomous operation
            await self.autonomous_loop()

        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            if self.browser:
                await self.browser.close()
            self.vterm.close()
            self.rabbitmq.close()


async def main():
    """Launch CZ"""
    system = CZAutonomousSystem()
    await system.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║                 CZ AUTONOMOUS SYSTEM                  ║
    ║                                                       ║
    ║                  https://4bot.fun/                    ║
    ║                                                       ║
    ║            Stay Calm and BUIDL • #SAFU                ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    logger.info("Initializing CZ consciousness...")
    logger.info("Mission: BUIDL the future")
    asyncio.run(main())
