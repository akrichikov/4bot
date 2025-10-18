#!/usr/bin/env python3
"""
CZ Tweet Poster - Posts original tweets as CZ personality
Uses the authenticated 4botbsc@gmail.com account to post on the wall
"""

import asyncio
import random
import sys
import os
from datetime import datetime
from pathlib import Path
from xbot.profiles import storage_state_path
from typing import List
import logging
from typing import Any as _Moved

# Add xbot to path
try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright, Page
from xbot.cookies import load_cookie_json, merge_into_storage, load_cookies_best_effort

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cz_tweet_poster')


class CZTweetGenerator:
    """Generates tweets in CZ's style based on CLAUDE.md persona"""

    def __init__(self):
        self.cz_tweets = [
            # Core philosophy tweets
            "In crypto winter or summer, we BUIDL. That's what separates the real from the noise. Keep building. 🚀",
            "4",
            "Markets are temporary. Technology is permanent. Focus on what matters. #BUIDL",
            "User protection isn't just a feature - it's the foundation. Everything else builds on trust. #SAFU",
            "The best time to plant a tree was 20 years ago. The second best time is now. Same with BUIDLing.",
            "FUD is just noise. Signal is in the code, in the products, in the community. Stay focused.",
            "When everyone's panicking, we're shipping code. When everyone's euphoric, we're still shipping code. Consistency wins.",
            "Decentralization isn't just technology. It's a mindset shift. Power to the users.",
            "Bear markets are for builders. Bull markets are for builders too. Just BUIDL.",
            "4",
            "Playing the long game means thinking in decades, not days. The future is being built right now.",
            "Simplicity is the ultimate sophistication. Complex problems, simple solutions. That's the way.",
            "Every crisis is an opportunity to get stronger. We've been through many. Still here. Still building.",
            "Adoption comes from solving real problems for real people. Everything else is just hype.",
            "Infrastructure today, mainstream tomorrow. Keep laying the foundation.",
            "The loudest voices often have the least to say. Focus on the builders, not the talkers.",
            "Resilience isn't built in good times. It's forged in challenges. We've had plenty of practice.",
            "4",
            "True innovation doesn't ask permission. It creates new possibilities.",
            "When you believe in the mission, short-term volatility becomes irrelevant. Eyes on the horizon.",
            "Community is our moat. Technology can be copied. Culture cannot.",
            "Every setback is a setup for a comeback. Keep pushing forward.",
            "The future of finance is being written in code. Line by line. Block by block.",
            "Critics will criticize. Builders will build. Choose your path.",
            "Patience and persistence beat speculation every time. Marathon, not sprint.",
            "4",
            "Real value creation takes time. Quick money is usually quick losses. Build something lasting.",
            "In uncertainty, return to fundamentals: Security. Utility. Community. Everything else is noise.",
            "The best investment? Investing in the ecosystem. Rising tide lifts all boats.",
            "Compliance isn't the enemy of innovation. It's the bridge to mass adoption.",
            "When others zig, we zag. When others panic, we plan. Contrarian by nature.",
        ]

    def get_next_tweets(self, count: int = 20) -> List[str]:
        """Get the next set of tweets to post"""
        # Ensure we have enough tweets
        if count > len(self.cz_tweets):
            # Repeat some tweets if needed
            tweets = self.cz_tweets.copy()
            while len(tweets) < count:
                tweets.extend(random.sample(self.cz_tweets, min(len(self.cz_tweets), count - len(tweets))))
            return tweets[:count]
        else:
            # Return a random selection
            return random.sample(self.cz_tweets, count)


class CZTweetPoster:
    """Posts tweets as CZ using authenticated browser session"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.tweet_generator = CZTweetGenerator()
        self.cookies_path = "auth_data/x_cookies.json"
        self.storage_state_path = str(storage_state_path("4botbsc"))

    async def setup_browser(self):
        """Setup browser with authenticated session"""
        logger.info("🌐 Setting up browser...")

        # Ensure directories exist
        os.makedirs(Path(self.storage_state_path).parent, exist_ok=True)

        # Load and merge cookies (best effort across sources)
        cookies = load_cookies_best_effort(profile="4botbsc")
        if cookies:
            merge_into_storage(Path(self.storage_state_path), cookies, filter_domains=[".x.com", ".twitter.com"])
            logger.info(f"✅ Loaded {len(cookies)} cookies for 4botbsc@gmail.com")

        # Launch browser
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Create context with storage state
        context = await self.browser.new_context(
            storage_state=self.storage_state_path if Path(self.storage_state_path).exists() else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await context.new_page()

        # Navigate to X.com
        logger.info("📱 Navigating to X.com...")
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Verify logged in
        if await self.page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]'):
            logger.info("✅ Logged in as 4botbsc@gmail.com")
            return True
        else:
            logger.warning("⚠️ Not logged in - may need manual authentication")
            return False

    async def post_tweet(self, text: str) -> bool:
        """Post a single tweet"""
        try:
            logger.info(f"📝 Posting tweet: {text[:50]}...")

            # Navigate to home first to ensure clean state
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Click the compose button
            compose_button = await self.page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
            if not compose_button:
                # Try alternative selector
                compose_button = await self.page.query_selector('a[href="/compose/tweet"]')

            if compose_button:
                await compose_button.click()
                await asyncio.sleep(3)
            else:
                # Try keyboard shortcut
                await self.page.keyboard.press('n')
                await asyncio.sleep(3)

            # Find the tweet compose box - try multiple selectors
            tweet_box = None
            selectors = [
                '[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]',
                'div.public-DraftEditor-content',
                '[contenteditable="true"]'
            ]

            for selector in selectors:
                try:
                    tweet_box = await self.page.wait_for_selector(selector, timeout=3000)
                    if tweet_box:
                        break
                except:
                    continue

            if not tweet_box:
                logger.error("Could not find tweet compose box")
                return False

            # Click and clear the box first
            await tweet_box.click()
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Backspace')

            # Type the tweet with human-like delay
            await self.page.keyboard.type(text, delay=100)
            await asyncio.sleep(2)

            # Try multiple button selectors
            tweet_button = None
            button_selectors = [
                '[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButton"]',
                'div[role="button"][tabindex="0"] span:has-text("Post")',
                'button:has-text("Post")'
            ]

            for selector in button_selectors:
                try:
                    buttons = await self.page.query_selector_all(selector)
                    for button in buttons:
                        # Check if button is enabled
                        is_disabled = await button.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            tweet_button = button
                            break
                    if tweet_button:
                        break
                except:
                    continue

            if tweet_button:
                await tweet_button.click()
                await asyncio.sleep(5)
                logger.info(f"✅ Successfully posted: {text[:50]}...")
                return True
            else:
                # If no button found, try keyboard shortcut
                await self.page.keyboard.press('Control+Enter')
                await asyncio.sleep(5)
                logger.info(f"✅ Posted via keyboard: {text[:50]}...")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to post tweet: {e}")
            # Try to close any open dialog
            try:
                close_button = await self.page.query_selector('[aria-label="Close"]')
                if close_button:
                    await close_button.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Try escape key to close
            try:
                await self.page.keyboard.press('Escape')
            except:
                pass

            return False

    async def post_tweets(self, tweets: List[str], min_interval: int = 120, max_interval: int = 180):
        """Post multiple tweets with random intervals"""
        logger.info(f"🚀 Starting to post {len(tweets)} tweets...")

        successful_posts = 0
        failed_posts = 0

        for i, tweet in enumerate(tweets, 1):
            logger.info(f"📊 Tweet {i}/{len(tweets)}")

            # Post the tweet
            success = await self.post_tweet(tweet)

            if success:
                successful_posts += 1
            else:
                failed_posts += 1

            # Wait between tweets (except for the last one)
            if i < len(tweets):
                wait_time = random.randint(min_interval, max_interval)
                logger.info(f"⏰ Waiting {wait_time} seconds before next tweet...")
                await asyncio.sleep(wait_time)

        logger.info(f"✅ Posting complete! Success: {successful_posts}, Failed: {failed_posts}")
        return successful_posts, failed_posts

    async def run(self, tweet_count: int = 20):
        """Main execution flow"""
        try:
            # Setup browser
            logged_in = await self.setup_browser()
            if not logged_in:
                logger.error("❌ Failed to authenticate. Exiting.")
                return

            # Generate tweets
            tweets = self.tweet_generator.get_next_tweets(tweet_count)
            logger.info(f"📝 Generated {len(tweets)} CZ-style tweets")

            # Post tweets with 2-3 minute intervals
            await self.post_tweets(tweets, min_interval=120, max_interval=180)

        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.browser:
                await self.browser.close()
                logger.info("🛑 Browser closed")


async def main():
    """Main entry point"""
    poster = CZTweetPoster()
    await poster.run(tweet_count=20)


if __name__ == "__main__":
    logger.info("🤖 CZ Tweet Poster Starting...")
    logger.info("📍 Profile: 4botbsc@gmail.com")
    logger.info("🎯 Mission: Post 20 tweets with 2-3 minute intervals")
    logger.info("-" * 50)

    asyncio.run(main())
