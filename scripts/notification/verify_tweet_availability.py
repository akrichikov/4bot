#!/usr/bin/env python3
"""
Tweet Availability Verification Script
Checks which tweets from the list are still accessible on X/Twitter
"""

import asyncio
from typing import Any as _Moved
import re
import json
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('VERIFY')


class TweetVerifier:
    """Verify tweet availability on X/Twitter"""

    def __init__(self):
        self.browser = None
        self.page = None
        from xbot.profiles import storage_state_path
        self.storage_state_path = str(storage_state_path("4botbsc"))
        self.tweet_file = str(Path("Docs/4Bot Tweets.md"))
        self.available_tweets = []
        self.unavailable_tweets = []

    def parse_tweet_urls(self) -> List[Dict[str, str]]:
        """Extract unique tweet URLs with metadata"""
        with open(self.tweet_file, 'r') as f:
            content = f.read()

        # Extract URLs with surrounding context
        urls_data = []
        lines = content.split('\n')
        url_pattern = r'https://x\.com/([^/\s]+)/status/(\d+)'

        seen = set()
        for i, line in enumerate(lines):
            matches = re.findall(url_pattern, line)
            for username, tweet_id in matches:
                url = f"https://x.com/{username}/status/{tweet_id}"
                if url not in seen:
                    seen.add(url)
                    urls_data.append({
                        'url': url,
                        'username': username,
                        'tweet_id': tweet_id,
                        'line_number': i + 1
                    })

        logger.info(f"📋 Found {len(urls_data)} unique tweet URLs to verify")
        return urls_data

    async def setup_browser(self):
        """Setup headless browser"""
        logger.info("🌐 Setting up browser for verification...")

        # Check authentication
        if Path(self.storage_state_path).exists():
            with open(self.storage_state_path, 'r') as f:
                storage_data = json.load(f)
                cookie_count = len(storage_data.get('cookies', []))
                logger.info(f"✅ Loaded {cookie_count} cookies")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await self.browser.new_context(
            storage_state=self.storage_state_path if Path(self.storage_state_path).exists() else None,
            viewport={"width": 1920, "height": 1080}
        )

        self.page = await context.new_page()

        # Navigate to home to establish session
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        logger.info("✅ Browser ready for verification")

    async def check_tweet(self, tweet_data: Dict[str, str]) -> bool:
        """Check if a single tweet is available"""
        try:
            url = tweet_data['url']

            # Navigate to tweet
            await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(2)

            # Check content
            content = await self.page.content()

            # Various indicators of unavailable tweets
            unavailable_indicators = [
                "doesn't exist",
                "this tweet is unavailable",
                "this post is unavailable",
                "account is suspended",
                "this account doesn't exist",
                "something went wrong",
                "page doesn't exist",
                "this post was deleted"
            ]

            is_unavailable = any(indicator in content.lower() for indicator in unavailable_indicators)

            # Check for actual tweet content indicators
            has_tweet_content = any([
                'data-testid="tweet"' in content,
                'data-testid="tweetText"' in content,
                f'@{tweet_data["username"]}' in content.lower(),
                'timeline-tweet' in content
            ])

            if is_unavailable or not has_tweet_content:
                return False

            return True

        except Exception as e:
            logger.debug(f"Error checking tweet: {e}")
            return False

    async def verify_all_tweets(self):
        """Verify all tweets from the file"""
        try:
            await self.setup_browser()

            tweets_data = self.parse_tweet_urls()
            total = len(tweets_data)

            logger.info("=" * 60)
            logger.info("🔍 TWEET AVAILABILITY VERIFICATION")
            logger.info(f"📊 Checking {total} unique tweets")
            logger.info("=" * 60)

            for i, tweet_data in enumerate(tweets_data):
                logger.info(f"[{i+1}/{total}] Checking @{tweet_data['username']} - {tweet_data['tweet_id']}")

                is_available = await self.check_tweet(tweet_data)

                if is_available:
                    self.available_tweets.append(tweet_data)
                    logger.info(f"  ✅ AVAILABLE")
                else:
                    self.unavailable_tweets.append(tweet_data)
                    logger.info(f"  ❌ UNAVAILABLE")

                # Progress report every 10
                if (i + 1) % 10 == 0:
                    available_count = len(self.available_tweets)
                    unavailable_count = len(self.unavailable_tweets)
                    logger.info(f"Progress: {i+1}/{total} - Available: {available_count} | Unavailable: {unavailable_count}")

                # Rate limiting
                await asyncio.sleep(2)

            # Generate report
            self.generate_report()

        except Exception as e:
            logger.error(f"Verification error: {e}")
        finally:
            if self.browser:
                await self.browser.close()

    def generate_report(self):
        """Generate availability report"""
        total = len(self.available_tweets) + len(self.unavailable_tweets)
        available_count = len(self.available_tweets)
        unavailable_count = len(self.unavailable_tweets)

        logger.info("=" * 60)
        logger.info("📊 VERIFICATION COMPLETE")
        logger.info(f"Total checked: {total}")
        logger.info(f"✅ Available: {available_count} ({available_count/total*100:.1f}%)")
        logger.info(f"❌ Unavailable: {unavailable_count} ({unavailable_count/total*100:.1f}%)")
        logger.info("=" * 60)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = str(Path("Docs/status") / f"tweet_availability_{timestamp}.json")

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_checked': total,
            'available_count': available_count,
            'unavailable_count': unavailable_count,
            'available_tweets': self.available_tweets,
            'unavailable_tweets': self.unavailable_tweets
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"📄 Report saved to: {report_file}")

        # Save available tweets to new file
        if self.available_tweets:
            available_file = str(Path("Docs/available_tweets.md"))
            with open(available_file, 'w') as f:
                f.write("# Available FUD Tweets for CZ Replies\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                for tweet in self.available_tweets:
                    f.write(f"- @{tweet['username']}: {tweet['url']}\n")
            logger.info(f"✅ Available tweets saved to: {available_file}")


async def main():
    verifier = TweetVerifier()
    await verifier.verify_all_tweets()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           TWEET AVAILABILITY VERIFICATION v1.0            ║
    ║                                                           ║
    ║        Checking which FUD tweets are still available      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
