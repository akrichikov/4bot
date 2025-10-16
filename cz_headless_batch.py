#!/usr/bin/env python3
"""
CZ Headless Batch Reply
Optimized headless version for finding and replying to non-4botbsc posts
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Set

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.facade import XBot
from xbot.cookies import load_cookie_json, merge_into_storage
from playwright.async_api import Page

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-HEADLESS] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_headless')


@dataclass
class Post:
    """Post to reply to"""
    id: str
    author: str
    content: str
    url: str


class CZQuickReplies:
    """Fast CZ-style reply generation"""

    @staticmethod
    def get_reply(content: str, author: str) -> str:
        """Generate quick CZ reply based on content"""
        content_lower = content.lower()

        # FUD detection
        if any(w in content_lower for w in ['scam', 'rug', 'ponzi', 'dead', 'crash']):
            return "4"

        # Building content
        if any(w in content_lower for w in ['build', 'buidl', 'ship', 'launch', 'deploy']):
            replies = [
                "This is the way! Keep BUIDLing 🚀",
                "Love to see it. We build through everything.",
                "Building is the answer. Always.",
            ]
            return random.choice(replies)

        # Questions
        if '?' in content:
            if 'when' in content_lower:
                return "The best time was yesterday, the next best time is today."
            elif 'how' in content_lower:
                return "Start small, learn constantly, build consistently."
            else:
                return "Focus on what you can control. BUIDL."

        # Market talk
        if any(w in content_lower for w in ['price', 'chart', 'pump', 'dump']):
            return "Less charts, more building."

        # Generic
        replies = [
            "Keep building! The future belongs to builders.",
            "BUIDL 🔨",
            "Long-term thinking always wins.",
            "Stay calm and keep building.",
            "Focus on building, not the noise.",
        ]
        return random.choice(replies)


class HeadlessBatchReplier:
    """Optimized headless batch replier"""

    def __init__(self):
        self.config = Config.from_env()
        self.config.headless = True  # ALWAYS headless
        self.config.persist_session = False  # In-memory only
        self.bot = XBot(self.config)
        self.replies = CZQuickReplies()
        self.own_handles = {'4botbsc', '4bot'}
        self.replied_count = 0
        self.max_replies = 50  # Safety limit

    def is_self_post(self, author: str) -> bool:
        """Check if post is from our account"""
        author_lower = author.lower()
        return any(h in author_lower for h in self.own_handles)

    async def collect_posts(self, page: Page) -> List[Post]:
        """Collect posts from current page"""
        posts = []

        script = """
        () => {
            const results = [];
            const articles = document.querySelectorAll('article[data-testid="tweet"]');

            articles.forEach(article => {
                try {
                    // Get text
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.textContent : '';

                    // Get author
                    const links = article.querySelectorAll('a[href^="/"]');
                    let author = '';
                    for (const link of links) {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\\/[^\\/]+$/) && !href.includes('status')) {
                            author = href.substring(1);
                            break;
                        }
                    }

                    // Get URL
                    const statusLink = article.querySelector('a[href*="/status/"]');
                    const url = statusLink ? statusLink.href : '';
                    const id = url ? url.split('/status/')[1]?.split('/')[0] : '';

                    if (id && text && author) {
                        results.push({
                            id: id,
                            author: author,
                            content: text.substring(0, 300),
                            url: url
                        });
                    }
                } catch (e) {}
            });
            return results;
        }
        """

        data = await page.evaluate(script)

        # Filter out self-posts
        for item in data:
            if not self.is_self_post(item['author']):
                posts.append(Post(
                    id=item['id'],
                    author=item['author'],
                    content=item['content'],
                    url=item['url']
                ))

        return posts

    async def run(self):
        """Run headless batch reply"""
        logger.info("🚀 Starting CZ Headless Batch Reply")
        logger.info("   Mode: HEADLESS ✅")
        logger.info("   Self-filter: ACTIVE ✅")
        logger.info("   Max replies: %d", self.max_replies)

        # Setup authentication
        from xbot.profiles import profile_paths
        # Prefer config/profiles path if present
        cfg_storage = Path("config/profiles/4botbsc/storageState.json")
        if cfg_storage.exists():
            self.config.storage_state = cfg_storage
            self.config.user_data_dir = Path(".x-user/4botbsc")
        else:
            storage, user_dir = profile_paths("4botbsc")
            self.config.storage_state = storage
            self.config.user_data_dir = user_dir

        # Load cookies
        cookie_path = Path("/Users/doctordre/projects/4bot/auth_data/x_cookies.json")
        if cookie_path.exists():
            cookies = load_cookie_json(cookie_path)
            merge_into_storage(
                Path(self.config.storage_state),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info("✅ Authentication configured")

        async with Browser(self.config, label="cz_headless") as browser:
            page = browser.page

            # Quick login check
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Verify login
            if not await page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]'):
                logger.error("❌ Not logged in - check authentication")
                return

            logger.info("✅ Logged in successfully")

            # Collect posts from timeline
            logger.info("📱 Scanning timeline...")
            timeline_posts = await self.collect_posts(page)
            logger.info(f"   Found {len(timeline_posts)} non-4botbsc posts")

            # Go to notifications
            await page.goto("https://x.com/notifications", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Collect notifications
            logger.info("🔔 Scanning notifications...")
            notif_posts = await self.collect_posts(page)
            logger.info(f"   Found {len(notif_posts)} non-4botbsc notifications")

            # Combine and deduplicate
            all_posts = {p.id: p for p in timeline_posts + notif_posts}.values()
            posts = list(all_posts)[:self.max_replies]

            logger.info(f"\n{'='*50}")
            logger.info(f"📊 READY TO REPLY:")
            logger.info(f"   Total posts: {len(posts)}")
            logger.info(f"   All from non-4botbsc accounts ✅")
            logger.info(f"{'='*50}\n")

            # Reply to posts
            for i, post in enumerate(posts, 1):
                try:
                    logger.info(f"[{i}/{len(posts)}] @{post.author}: {post.content[:50]}...")

                    # Generate reply
                    reply = self.replies.get_reply(post.content, post.author)
                    logger.info(f"   → Reply: {reply}")

                    # Post reply
                    if post.url:
                        await self.bot.reply(post.url, reply)
                        self.replied_count += 1
                        logger.info(f"   ✅ Posted!")

                    # Rate limit delay
                    if i < len(posts):
                        delay = random.uniform(3, 6)
                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"   ❌ Error: {e}")

            # Summary
            logger.info(f"\n{'='*50}")
            logger.info(f"✅ COMPLETE!")
            logger.info(f"   Replies posted: {self.replied_count}")
            logger.info(f"   Success rate: {(self.replied_count/len(posts)*100):.1f}%")
            logger.info(f"{'='*50}")


async def main():
    """Main entry point"""
    try:
        replier = HeadlessBatchReplier()
        await replier.run()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CZ Headless Batch Reply System                     ║
║                                                              ║
║  🚀 Running in HEADLESS mode (no browser window)            ║
║  🔒 Self-post filtering ACTIVE                              ║
║  ⚡ Optimized for speed and efficiency                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())
