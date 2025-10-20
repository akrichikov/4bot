#!/usr/bin/env python3
"""
Headless monitor that runs in background and logs intercepted posts.
Logs to both console and file for verification.
"""

import asyncio
from typing import Any as _Moved
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import logging

from xbot.config import Config
from xbot.utils import log_file

# Setup logging to both file and console
_cfg = Config.from_env()
logs_dir = Path(_cfg.logs_dir) / 'monitor'
logs_dir.mkdir(parents=True, exist_ok=True)
log_file = str(logs_dir / f'headless_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HeadlessMonitor:
    """Headless monitoring with comprehensive logging."""

    def __init__(self):
        self.posts_intercepted = []
        self.running = True

    async def monitor_headless(self, duration_seconds=300):
        """Run headless monitoring for specified duration."""

        logger.info("=" * 70)
        logger.info("HEADLESS POST MONITOR STARTED")
        logger.info(f"Log file: {log_file}")
        logger.info(f"Duration: {duration_seconds} seconds")
        logger.info("=" * 70)

        # Load cookies via centralized helper (best-effort)
        try:
            from xbot.cookies import load_cookies_best_effort
            cfg = _cfg
            cookies = load_cookies_best_effort(profile=cfg.profile_name)
            logger.info(f"Loaded {len(cookies)} cookies via helper for profile={cfg.profile_name}")
        except Exception as e:
            logger.warning(f"Cookie load failed via helper: {e}; falling back to chrome_profiles default")
            cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
            cookies = json.loads(cookie_file.read_text(encoding='utf-8')) if cookie_file.exists() else []

        playwright = await async_playwright().start()

        try:
            # Launch browser in headless mode
            browser = await playwright.chromium.launch(
                headless=True,  # Running headless
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Enhanced console handler that logs everything
            def handle_console(msg):
                text = msg.text
                if '__POST_EVENT__' in text:
                    try:
                        # Extract JSON from console message
                        json_str = text.split('__POST_EVENT__:')[1]
                        post_data = json.loads(json_str)

                        # Log the intercepted post
                        logger.info("=" * 70)
                        logger.info("🔴 POST INTERCEPTED!")
                        logger.info(f"Author: @{post_data.get('handle', 'unknown')}")
                        logger.info(f"Name: {post_data.get('author', 'Unknown')}")
                        logger.info(f"Content: {post_data.get('content', '')}")
                        logger.info(f"Likes: {post_data.get('likes', 0)}")
                        logger.info(f"Retweets: {post_data.get('retweets', 0)}")
                        logger.info(f"Post ID: {post_data.get('id', 'unknown')}")
                        logger.info(f"Timestamp: {post_data.get('timestamp', '')}")
                        logger.info("=" * 70)

                        self.posts_intercepted.append(post_data)

                        # Special alert for AI-related posts
                        content_lower = post_data.get('content', '').lower()
                        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'gpt', 'llm',
                                      'neural', 'deep learning', 'chatbot', 'automation']

                        if any(keyword in content_lower for keyword in ai_keywords):
                            logger.info("⚠️ AI-RELATED POST DETECTED! ⚠️")
                            logger.info("This post contains AI-related content")

                            # Save to special file
                            results_dir = Path(_cfg.report_html_outdir)
                            results_dir.mkdir(parents=True, exist_ok=True)
                            with open(results_dir / 'ai_posts_intercepted.json', 'a', encoding='utf-8') as f:
                                json.dump(post_data, f)
                                f.write('\n')

                    except Exception as e:
                        logger.error(f"Error parsing post data: {e}")

            page.on("console", handle_console)

            # Navigate
            logger.info("Connecting to X.com...")
            await page.goto('https://x.com/home', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject the observer script
            observer_script = """
            (() => {
                console.log('Headless monitor observer starting...');
                const seenPosts = new Set();

                function extractPost(article) {
                    try {
                        const link = article.querySelector('a[href*="/status/"]');
                        if (!link) return null;

                        const postId = link.href.split('/status/')[1]?.split('?')[0];
                        if (!postId || seenPosts.has(postId)) return null;

                        seenPosts.add(postId);

                        // Extract author
                        const userElement = article.querySelector('[data-testid="User-Name"]');
                        let authorName = 'Unknown';
                        let authorHandle = 'unknown';

                        if (userElement) {
                            const nameSpan = userElement.querySelector('span');
                            if (nameSpan) authorName = nameSpan.textContent;

                            const handleLink = userElement.querySelector('a[href^="/"]');
                            if (handleLink) {
                                authorHandle = handleLink.href.split('/').pop();
                            }
                        }

                        // Extract content
                        const tweetText = article.querySelector('[data-testid="tweetText"]');
                        const content = tweetText ? tweetText.textContent : '';

                        // Extract metrics
                        const replyBtn = article.querySelector('[data-testid="reply"]');
                        const retweetBtn = article.querySelector('[data-testid="retweet"]');
                        const likeBtn = article.querySelector('[data-testid="like"],[data-testid="unlike"]');

                        const postData = {
                            id: postId,
                            author: authorName,
                            handle: authorHandle,
                            content: content,
                            replies: replyBtn?.querySelector('span')?.textContent || '0',
                            retweets: retweetBtn?.querySelector('span')?.textContent || '0',
                            likes: likeBtn?.querySelector('span')?.textContent || '0',
                            timestamp: new Date().toISOString()
                        };

                        console.log('__POST_EVENT__:' + JSON.stringify(postData));
                        return postData;
                    } catch (error) {
                        return null;
                    }
                }

                // Process existing posts
                document.querySelectorAll('article').forEach(extractPost);

                // Monitor for new posts
                const observer = new MutationObserver((mutations) => {
                    for (const mutation of mutations) {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const articles = node.tagName === 'ARTICLE' ? [node] :
                                                (node.querySelectorAll ? node.querySelectorAll('article') : []);
                                articles.forEach(extractPost);
                            }
                        }
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                return 'Monitor active';
            })();
            """

            await page.evaluate(observer_script)
            logger.info("Observer injected successfully")
            logger.info("Monitoring for new posts...")

            # Monitor for the specified duration
            start_time = asyncio.get_event_loop().time()
            last_scroll = 0
            last_refresh = 0

            while self.running and (asyncio.get_event_loop().time() - start_time < duration_seconds):
                await asyncio.sleep(1)

                # Scroll every 10 seconds
                if asyncio.get_event_loop().time() - last_scroll > 10:
                    await page.evaluate("window.scrollBy(0, 300)")
                    logger.info(f"Scrolling... [{int(asyncio.get_event_loop().time() - start_time)}s elapsed]")
                    last_scroll = asyncio.get_event_loop().time()

                # Refresh feed every 30 seconds to catch new posts
                if asyncio.get_event_loop().time() - last_refresh > 30:
                    await page.reload()
                    await asyncio.sleep(3)
                    await page.evaluate(observer_script)
                    logger.info("Feed refreshed")
                    last_refresh = asyncio.get_event_loop().time()

            # Final summary
            logger.info("=" * 70)
            logger.info("MONITORING COMPLETE")
            logger.info(f"Total posts intercepted: {len(self.posts_intercepted)}")
            logger.info(f"Log saved to: {log_file}")

            # Save all intercepted posts to JSON
            with open(results_dir / f'intercepted_posts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(self.posts_intercepted, f, indent=2)

            logger.info("=" * 70)

            await browser.close()

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()


async def main():
    """Run the headless monitor."""
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # Default 5 minutes

    monitor = HeadlessMonitor()
    await monitor.monitor_headless(duration_seconds=duration)


if __name__ == "__main__":
    print(f"Starting headless monitor...")
    print(f"Logs will be saved to: {log_file}")
    print("Press Ctrl+C to stop monitoring")
    asyncio.run(main())
