#!/usr/bin/env python3
"""
CZ Reply to Specific Tweets
Parses the 4Bot Tweets.md file and replies to each URL as CZ
"""

import asyncio
import json
import logging
import random
import re
import sys
import time
from pathlib import Path
from typing import List

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.facade import XBot
from xbot.cookies import load_cookie_json, merge_into_storage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-TWEETS] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_tweets')


class CZTweetReplier:
    """Reply to specific tweets from markdown file"""

    def __init__(self):
        self.config = Config.from_env()
        self.config.headless = True  # Run headless
        self.config.persist_session = False
        self.bot = XBot(self.config)
        self.replied_count = 0
        self.failed_count = 0

    def extract_urls(self, file_path: str) -> List[str]:
        """Extract all tweet URLs from markdown file"""
        urls = []
        with open(file_path, 'r') as f:
            content = f.read()

        # Find all X.com/Twitter URLs
        pattern = r'https://x\.com/[^/]+/status/\d+'
        urls = re.findall(pattern, content)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"📋 Found {len(unique_urls)} unique tweet URLs")
        return unique_urls

    def generate_cz_reply(self, url: str, index: int) -> str:
        """Generate contextual CZ reply based on URL position"""

        # Mix of CZ responses for variety
        responses = [
            # FUD fighters
            "4",
            "4. Back to building.",
            "4 🤷‍♂️",

            # Building focused
            "Less noise, more signal. BUIDL.",
            "Keep building! The future belongs to builders.",
            "This is the way. We build through everything.",
            "BUIDL through all market conditions 🚀",
            "Focus on what you can control. Build.",
            "Building is the answer. Always has been.",
            "Winners focus on winning. Losers focus on winners.",

            # Long-term vision
            "Long-term thinking always wins.",
            "Play the long game. Short-term is noise.",
            "Think in decades, not days.",
            "The best time was yesterday, the next best time is today.",
            "Patience and building. That's the formula.",

            # Encouragement
            "We're all gonna make it. Just keep building.",
            "This is the mindset. Keep pushing forward.",
            "Together we build the future.",
            "Stay calm and keep building.",
            "Every builder counts. Every line of code matters.",

            # Market wisdom
            "Markets go up and down. We build through it all.",
            "Price is noise. Building is signal.",
            "Less charts, more code.",
            "Bear or bull, we BUIDL.",

            # Community
            "Builders > Speculators. Always.",
            "The community that builds together, wins together.",
            "Real value comes from building, not speculation.",
            "Support builders, ignore FUDders.",

            # Security
            "Security first. Always. #SAFU",
            "Build safe. Build strong. Build for users.",
            "User protection is everything.",
        ]

        # For the first few, use "4" more often (fighting FUD)
        if index < 20:
            if random.random() < 0.4:  # 40% chance
                return "4"

        # Mix responses for variety
        return random.choice(responses)

    async def reply_to_url(self, url: str, reply_text: str) -> bool:
        """Reply to a specific tweet URL"""
        try:
            await self.bot.reply(url, reply_text)
            return True
        except Exception as e:
            logger.error(f"Failed to reply: {e}")
            return False

    async def run(self):
        """Main execution"""
        logger.info("🚀 Starting CZ Tweet Reply Process")
        logger.info("   Mode: HEADLESS")
        logger.info("   Target: /Users/doctordre/projects/4bot/Docs/4Bot Tweets.md")

        # Extract URLs from markdown
        urls = self.extract_urls('/Users/doctordre/projects/4bot/Docs/4Bot Tweets.md')

        if not urls:
            logger.error("No URLs found in file")
            return

        # Setup browser
        from xbot.profiles import profile_paths
        storage, user_dir = profile_paths("4botbsc")
        self.config.storage_state = storage
        self.config.user_data_dir = user_dir

        # Load cookies for authentication
        cookie_path = Path("/Users/doctordre/projects/4bot/auth_data/x_cookies.json")
        if cookie_path.exists():
            cookies = load_cookie_json(cookie_path)
            merge_into_storage(
                Path(storage),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info("✅ Authentication configured")

        async with Browser(self.config, label="cz_tweet_replier") as browser:
            page = browser.page

            # Login if needed
            await login_if_needed(page, self.config)
            logger.info("✅ Logged in as 4botbsc@gmail.com")

            # Process each URL
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 Processing {len(urls)} tweets...")
            logger.info(f"{'='*60}\n")

            for i, url in enumerate(urls, 1):
                try:
                    # Extract username from URL for logging
                    username = url.split('/')[3]
                    status_id = url.split('/status/')[1]

                    logger.info(f"[{i}/{len(urls)}] @{username} - Status: {status_id}")

                    # Generate CZ reply
                    reply = self.generate_cz_reply(url, i)
                    logger.info(f"   Reply: {reply}")

                    # Post the reply
                    success = await self.reply_to_url(url, reply)

                    if success:
                        self.replied_count += 1
                        logger.info(f"   ✅ Posted successfully!")
                    else:
                        self.failed_count += 1
                        logger.info(f"   ❌ Failed to post")

                    # Rate limiting - wait between replies
                    if i < len(urls):
                        delay = random.uniform(5, 10)  # 5-10 seconds
                        logger.info(f"   Waiting {delay:.1f}s...")
                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"   Error processing URL {url}: {e}")
                    self.failed_count += 1
                    continue

            # Final summary
            logger.info(f"\n{'='*60}")
            logger.info(f"🎉 BATCH COMPLETE!")
            logger.info(f"   Total URLs: {len(urls)}")
            logger.info(f"   ✅ Successful replies: {self.replied_count}")
            logger.info(f"   ❌ Failed replies: {self.failed_count}")
            logger.info(f"   Success rate: {(self.replied_count/len(urls)*100):.1f}%")
            logger.info(f"{'='*60}")

            # Save summary
            summary = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_urls": len(urls),
                "replied": self.replied_count,
                "failed": self.failed_count,
                "urls_processed": urls
            }

            log_path = Path("/Users/doctordre/projects/4bot/logs/tweet_reply_summary.json")
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, 'w') as f:
                json.dump(summary, f, indent=2)

            logger.info(f"\n📄 Summary saved to: {log_path}")


async def main():
    """Main entry point"""
    try:
        replier = CZTweetReplier()
        await replier.run()
    except KeyboardInterrupt:
        logger.info("\n⛔ Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CZ Tweet Reply System                              ║
║                                                              ║
║  📋 Parsing: /Docs/4Bot Tweets.md                           ║
║  🤖 Replying as: CZ (4botbsc@gmail.com)                     ║
║  🚀 Mode: HEADLESS                                          ║
║  💬 Persona: CZ - "4" for FUD, BUIDL for everything        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())