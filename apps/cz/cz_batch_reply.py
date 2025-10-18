#!/usr/bin/env python3
"""
CZ Batch Reply Script
Finds all posts/messages NOT from 4botbsc and replies to them as CZ
"""

import asyncio
import json
import logging
from typing import Any as _Moved
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.facade import XBot
from playwright.async_api import Page
from xbot.cz_reply import CZReplyGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-BATCH] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_batch')


@dataclass
class Post:
    """Represents a post to reply to"""
    id: str
    author: str
    content: str
    url: str
    is_mention: bool = False
    is_reply: bool = False
    timestamp: Optional[str] = None


class CZBatchResponder:
    def __init__(self):
        # Use the shared deterministic generator
        self.generator = CZReplyGenerator()

    def generate_reply(self, post: Post) -> str:
        return self.generator.generate(post.author, post.content, post.url)


class PostCollector:
    """Collects posts from timeline and notifications"""

    def __init__(self, page: Page):
        self.page = page
        self.posts: List[Post] = []
        self.seen_ids: Set[str] = set()

    async def collect_timeline_posts(self, max_posts: int = 50) -> List[Post]:
        """Collect posts from timeline"""
        logger.info("📱 Scanning timeline for posts...")

        # Navigate to home
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Inject collection script
        collection_script = """
        () => {
            const posts = [];
            const articles = document.querySelectorAll('article[data-testid="tweet"]');

            articles.forEach(article => {
                try {
                    // Get post text
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.textContent : '';

                    // Get author
                    const authorLinks = article.querySelectorAll('a[href^="/"]');
                    let author = 'unknown';
                    for (const link of authorLinks) {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\\/[^\\/]+$/) && !href.includes('/status/')) {
                            author = href.substring(1);
                            break;
                        }
                    }

                    // Get post ID/URL
                    const statusLink = article.querySelector('a[href*="/status/"]');
                    const url = statusLink ? statusLink.href : '';
                    const postId = url ? url.split('/status/')[1]?.split('/')[0] : '';

                    // Skip if no valid data
                    if (!postId || !text) return;

                    // Check if it's a reply or mention
                    const isReply = text.includes('@4botbsc') || text.includes('@4bot');

                    posts.push({
                        id: postId,
                        author: author,
                        content: text.substring(0, 500),
                        url: url,
                        is_mention: isReply,
                        is_reply: isReply
                    });
                } catch (e) {
                    console.error('Error extracting post:', e);
                }
            });

            return posts;
        }
        """

        posts_data = await self.page.evaluate(collection_script)

        # Filter out 4botbsc posts
        filtered_posts = []
        for post_data in posts_data:
            # Skip if from 4botbsc or 4bot
            author_lower = post_data['author'].lower()
            if '4botbsc' in author_lower or author_lower == '4bot':
                logger.debug(f"Filtered out self-post from @{post_data['author']}")
                continue

            # Skip if already seen
            if post_data['id'] in self.seen_ids:
                continue

            self.seen_ids.add(post_data['id'])

            post = Post(
                id=post_data['id'],
                author=post_data['author'],
                content=post_data['content'],
                url=post_data['url'],
                is_mention=post_data.get('is_mention', False),
                is_reply=post_data.get('is_reply', False)
            )
            filtered_posts.append(post)

            if len(filtered_posts) >= max_posts:
                break

        logger.info(f"📊 Collected {len(filtered_posts)} non-4botbsc posts from timeline")
        return filtered_posts

    async def collect_notifications(self, max_posts: int = 30) -> List[Post]:
        """Collect posts from notifications"""
        logger.info("🔔 Scanning notifications...")

        # Navigate to notifications
        await self.page.goto("https://x.com/notifications", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Click on Mentions tab if available
        try:
            mentions_tab = await self.page.query_selector('a[href="/notifications/mentions"]')
            if mentions_tab:
                await mentions_tab.click()
                await asyncio.sleep(2)
                logger.info("📍 Switched to mentions tab")
        except:
            pass

        # Collect notification posts
        notification_script = """
        () => {
            const notifications = [];
            const items = document.querySelectorAll('[data-testid="cellInnerDiv"]');

            items.forEach(item => {
                try {
                    // Get text content
                    const text = item.textContent || '';

                    // Extract author handle
                    const userLink = item.querySelector('a[href^="/"][role="link"]');
                    const author = userLink ? userLink.getAttribute('href').substring(1).split('/')[0] : 'unknown';

                    // Look for tweet links
                    const tweetLink = item.querySelector('a[href*="/status/"]');
                    const url = tweetLink ? tweetLink.href : '';
                    const postId = url ? url.split('/status/')[1]?.split('/')[0] : '';

                    // Skip if no valid data or if it's just a follow notification
                    if (!postId || text.includes('followed you')) return;

                    notifications.push({
                        id: postId || 'notif_' + Date.now(),
                        author: author,
                        content: text.substring(0, 500),
                        url: url || 'https://x.com/notifications',
                        is_mention: true,
                        is_reply: true
                    });
                } catch (e) {
                    console.error('Error extracting notification:', e);
                }
            });

            return notifications;
        }
        """

        notif_data = await self.page.evaluate(notification_script)

        # Filter out 4botbsc notifications
        filtered_notifs = []
        for notif in notif_data:
            author_lower = notif['author'].lower()
            if '4botbsc' in author_lower or author_lower == '4bot':
                logger.debug(f"Filtered out self-notification from @{notif['author']}")
                continue

            if notif['id'] in self.seen_ids:
                continue

            self.seen_ids.add(notif['id'])

            post = Post(
                id=notif['id'],
                author=notif['author'],
                content=notif['content'],
                url=notif['url'],
                is_mention=True,
                is_reply=True
            )
            filtered_notifs.append(post)

            if len(filtered_notifs) >= max_posts:
                break

        logger.info(f"📊 Collected {len(filtered_notifs)} non-4botbsc notifications")
        return filtered_notifs


class CZBatchReplier:
    """Main batch reply orchestrator"""

    def __init__(self):
        self.config = Config.from_env()
        self.config.headless = True  # Headless mode for production
        self.bot = XBot(self.config)
        self.generator = CZBatchResponder()
        self.reply_delay = 5  # Seconds between replies

    async def run(self):
        """Run the batch reply process"""
        logger.info("🚀 Starting CZ Batch Reply Process (HEADLESS MODE)")
        logger.info("   Profile: 4botbsc")
        logger.info("   Filtering: Excluding all 4botbsc posts")
        logger.info("   Mode: Headless ✅")

        # Setup browser with authentication
        from xbot.profiles import profile_paths
        from xbot.cookies import load_cookie_json, merge_into_storage

        storage, user_dir = profile_paths("4botbsc")
        self.config.storage_state = storage
        self.config.user_data_dir = user_dir

        # Ensure cookies are loaded for headless auth
        cookie_path = Path("auth_data/x_cookies.json")
        if cookie_path.exists():
            cookies = load_cookie_json(cookie_path)
            merge_into_storage(
                Path(storage),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info(f"✅ Loaded {len(cookies)} cookies for authentication")

        async with Browser(self.config, label="cz_batch") as browser:
            page = browser.page

            # Login if needed
            await login_if_needed(page, self.config)

            # Create collector
            collector = PostCollector(page)

            # Collect posts from timeline
            timeline_posts = await collector.collect_timeline_posts(max_posts=30)

            # Collect posts from notifications
            notification_posts = await collector.collect_notifications(max_posts=20)

            # Combine all posts
            all_posts = timeline_posts + notification_posts

            # Remove duplicates based on ID
            unique_posts = {post.id: post for post in all_posts}.values()
            posts_to_reply = list(unique_posts)

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 SUMMARY:")
            logger.info(f"   Total posts found: {len(posts_to_reply)}")
            logger.info(f"   From timeline: {len(timeline_posts)}")
            logger.info(f"   From notifications: {len(notification_posts)}")
            logger.info(f"   All from non-4botbsc accounts ✅")
            logger.info(f"{'='*60}\n")

            if not posts_to_reply:
                logger.info("No posts to reply to. Exiting.")
                return

            # Confirm before proceeding
            logger.info("🤖 Starting batch replies...")

            # Reply to each post
            success_count = 0
            fail_count = 0

            for i, post in enumerate(posts_to_reply, 1):
                try:
                    logger.info(f"\n[{i}/{len(posts_to_reply)}] Processing post from @{post.author}")
                    logger.info(f"   Content: {post.content[:100]}...")

                    # Generate reply
                    reply = self.generator.generate_reply(post)
                    logger.info(f"   Reply: {reply}")

                    # Post the reply
                    if post.url and '/status/' in post.url:
                        await self.bot.reply(post.url, reply)
                        success_count += 1
                        logger.info(f"   ✅ Reply posted successfully!")
                    else:
                        logger.warning(f"   ⚠️ Invalid URL, skipping")
                        fail_count += 1

                    # Delay between replies
                    if i < len(posts_to_reply):
                        delay = random.uniform(self.reply_delay, self.reply_delay * 1.5)
                        logger.info(f"   Waiting {delay:.1f}s before next reply...")
                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"   ❌ Error replying to post: {e}")
                    fail_count += 1
                    continue

            # Final summary
            logger.info(f"\n{'='*60}")
            logger.info(f"🎉 BATCH REPLY COMPLETE!")
            logger.info(f"   Successful replies: {success_count}")
            logger.info(f"   Failed replies: {fail_count}")
            logger.info(f"   Total processed: {len(posts_to_reply)}")
            logger.info(f"   Success rate: {(success_count/len(posts_to_reply)*100):.1f}%")
            logger.info(f"{'='*60}")


async def main():
    """Main entry point"""

    # Save batch run log
    batch_log = {
        "timestamp": datetime.now().isoformat(),
        "profile": "4botbsc",
        "mode": "batch_reply"
    }

    try:
        replier = CZBatchReplier()
        await replier.run()

        batch_log["status"] = "success"

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        batch_log["status"] = "error"
        batch_log["error"] = str(e)

    # Save log
    log_path = Path("logs/cz_batch_log.json")
    log_path.parent.mkdir(exist_ok=True)

    with open(log_path, 'w') as f:
        json.dump(batch_log, f, indent=2)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║              CZ Batch Reply System v1.0                      ║
║                                                              ║
║  🤖 Finding all non-4botbsc posts and replying as CZ        ║
║  🔍 Scanning timeline and notifications                     ║
║  🚫 Filtering out all 4botbsc/4bot posts                   ║
║  💬 Generating contextual CZ responses                      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
