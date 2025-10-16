#!/usr/bin/env python3
"""Monitor @4botbsc mentions and auto-reply."""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

class MentionMonitor:
    def __init__(self):
        self.storage_path = Path("/Users/doctordre/projects/4bot/auth/4botbsc/storageState.json")
        self.replied_tweets_file = Path("/Users/doctordre/projects/4bot/replied_mentions.json")
        self.replied_tweets = self._load_replied_tweets()

    def _load_replied_tweets(self):
        """Load list of tweets we've already replied to."""
        if self.replied_tweets_file.exists():
            with open(self.replied_tweets_file) as f:
                return set(json.load(f))
        return set()

    def _save_replied_tweet(self, tweet_id: str):
        """Save tweet ID to avoid duplicate replies."""
        self.replied_tweets.add(tweet_id)
        with open(self.replied_tweets_file, 'w') as f:
            json.dump(list(self.replied_tweets), f, indent=2)

    async def check_mentions(self):
        """Check for new @4botbsc mentions."""
        print(f"\n{'='*70}")
        print(f"🔍 Checking mentions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            context = await browser.new_context(storage_state=str(self.storage_path))
            page = await context.new_page()

            # Go to notifications page
            print("📬 Loading notifications...")
            await page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Find mention tweets
            print("🔎 Looking for mentions...")
            try:
                # Look for tweets in the timeline
                articles = await page.query_selector_all('article[data-testid="tweet"]')
                print(f"📊 Found {len(articles)} potential mentions")

                new_mentions = []
                for article in articles[:10]:  # Check first 10 tweets
                    try:
                        # Get tweet link
                        links = await article.query_selector_all('a[href*="/status/"]')
                        for link in links:
                            href = await link.get_attribute('href')
                            if '/status/' in href:
                                tweet_id = href.split('/status/')[1].split('?')[0]
                                if tweet_id not in self.replied_tweets:
                                    tweet_url = f"https://x.com{href}" if href.startswith('/') else href
                                    new_mentions.append((tweet_id, tweet_url))
                                    print(f"  ✨ New mention found: {tweet_id}")
                                break
                    except Exception as e:
                        continue

                await browser.close()

                if new_mentions:
                    print(f"\n🎯 Found {len(new_mentions)} new mentions to reply to")
                    return new_mentions
                else:
                    print("✅ No new mentions (or all already replied)")
                    return []

            except Exception as e:
                print(f"❌ Error checking mentions: {e}")
                await browser.close()
                return []

    async def reply_to_mention(self, tweet_id: str, tweet_url: str):
        """Reply to a specific mention."""
        print(f"\n{'─'*70}")
        print(f"💬 Replying to tweet: {tweet_id}")
        print(f"🔗 URL: {tweet_url}")

        # Generate CZ-style response
        responses = [
            "4",
            "4.",
            "4. BUIDL > FUD",
            "4. We keep building.",
            "4. Focus on the work.",
            "BUIDL.",
        ]
        import random
        response = random.choice(responses)

        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            context = await browser.new_context(storage_state=str(self.storage_path))
            page = await context.new_page()

            try:
                # Navigate to tweet
                await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Click reply
                reply_button = await page.wait_for_selector('[data-testid="reply"]', timeout=10000)
                await reply_button.click()
                await asyncio.sleep(2)

                # Type response
                text_area = await page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
                await text_area.click()
                await asyncio.sleep(0.5)

                for char in response:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.03)

                await asyncio.sleep(1)

                # Submit
                await page.keyboard.press('Control+Enter')
                await asyncio.sleep(3)

                print(f"✅ Replied with: \"{response}\"")
                self._save_replied_tweet(tweet_id)

                await asyncio.sleep(5)
                await browser.close()
                return True

            except Exception as e:
                print(f"❌ Failed to reply: {e}")
                await browser.close()
                return False

    async def run_once(self):
        """Check mentions and reply once."""
        mentions = await self.check_mentions()

        if mentions:
            for tweet_id, tweet_url in mentions:
                success = await self.reply_to_mention(tweet_id, tweet_url)
                if success:
                    await asyncio.sleep(10)  # Wait between replies
                else:
                    await asyncio.sleep(5)

        print(f"\n{'='*70}")
        print(f"✅ Mention check complete")
        print(f"{'='*70}\n")

    async def run_loop(self, interval_minutes=15):
        """Run monitoring loop."""
        print(f"🤖 @4botbsc Mention Monitor Started")
        print(f"⏰ Checking every {interval_minutes} minutes")
        print(f"{'='*70}\n")

        while True:
            try:
                await self.run_once()
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")

            print(f"⏰ Sleeping for {interval_minutes} minutes...")
            await asyncio.sleep(interval_minutes * 60)

if __name__ == "__main__":
    import sys

    monitor = MentionMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Run once and exit
        asyncio.run(monitor.run_once())
    else:
        # Run continuously
        asyncio.run(monitor.run_loop(interval_minutes=15))
