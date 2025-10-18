#!/usr/bin/env python3
"""
Working live monitor that properly captures and displays posts.
Fixed version based on diagnostic results.
"""

import asyncio
from typing import Any as _Moved
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from collections import deque


class WorkingLiveMonitor:
    """Live monitoring that actually captures posts."""

    def __init__(self):
        self.posts_seen = set()
        self.post_count = 0
        self.posts_buffer = deque(maxlen=100)

    async def monitor_posts(self, duration_seconds=60):
        """Monitor X/Twitter for live posts."""

        print("""
╔══════════════════════════════════════════════════════════════════╗
║              LIVE X/TWITTER POST MONITOR                         ║
║                                                                  ║
║  Posts will appear below as they are detected                   ║
║  Account: akrichikov@gmail.com (test account)                   ║
╚══════════════════════════════════════════════════════════════════╝
        """)

        # Load cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        print(f"🍪 Loaded {len(cookies)} cookies")
        print(f"⏱️ Monitoring for {duration_seconds} seconds")
        print(f"📡 Posts will appear below...\n")

        playwright = await async_playwright().start()

        try:
            # Launch browser
            browser = await playwright.chromium.launch(
                headless=True,  # Headless for cleaner output
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Enhanced console handler
            def handle_console(msg):
                text = msg.text
                # Debug: show all console messages for now
                if '__POST_EVENT__' in text:
                    print(f"🔴 POST EVENT: {text}")
                elif '[TEST]' not in text and 'Error' not in text:
                    # Show other relevant console messages
                    if len(text) > 0 and text != 'undefined':
                        print(f"📝 Console: {text[:100]}")

            page.on("console", handle_console)

            # Navigate
            print("🌐 Connecting to X.com...")
            await page.goto('https://x.com/home', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Check initial posts
            articles = await page.query_selector_all('article')
            print(f"✅ Connected! Found {len(articles)} posts initially\n")

            # Enhanced observer script that extracts and logs posts
            observer_script = """
            (() => {
                console.log('Starting enhanced post monitor...');
                const seenPosts = new Set();
                let postCount = 0;

                function extractPost(article) {
                    try {
                        // Get post ID from status link
                        const link = article.querySelector('a[href*="/status/"]');
                        if (!link) return null;

                        const postId = link.href.split('/status/')[1]?.split('?')[0];
                        if (!postId || seenPosts.has(postId)) return null;

                        seenPosts.add(postId);
                        postCount++;

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

                        const replies = replyBtn?.querySelector('span')?.textContent || '0';
                        const retweets = retweetBtn?.querySelector('span')?.textContent || '0';
                        const likes = likeBtn?.querySelector('span')?.textContent || '0';

                        // Build post data
                        const postData = {
                            id: postId,
                            author: authorName,
                            handle: authorHandle,
                            content: content.substring(0, 280),
                            replies: replies,
                            retweets: retweets,
                            likes: likes,
                            timestamp: new Date().toISOString()
                        };

                        // Send to Python
                        console.log('__POST_EVENT__:' + JSON.stringify(postData));

                        return postData;
                    } catch (error) {
                        console.error('Error extracting post:', error);
                        return null;
                    }
                }

                // Process existing posts
                const existingArticles = document.querySelectorAll('article');
                console.log(`Processing ${existingArticles.length} existing posts...`);
                existingArticles.forEach(article => extractPost(article));

                // Monitor for new posts
                const observer = new MutationObserver((mutations) => {
                    for (const mutation of mutations) {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const articles = node.tagName === 'ARTICLE' ? [node] :
                                                (node.querySelectorAll ? node.querySelectorAll('article') : []);

                                articles.forEach(article => {
                                    const post = extractPost(article);
                                    if (post) {
                                        console.log(`New post detected: @${post.handle}`);
                                    }
                                });
                            }
                        }
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                console.log('Post monitor active. Total posts found: ' + postCount);
                return postCount;
            })();
            """

            # Inject observer
            initial_count = await page.evaluate(observer_script)
            print(f"📊 Observer injected, found {initial_count} posts\n")

            # Monitor for the specified duration
            start_time = asyncio.get_event_loop().time()
            last_scroll = 0

            # Process console messages and display posts
            displayed_posts = set()

            async def check_for_posts():
                """Check page console for post events."""
                # This would normally process the console messages
                # For now we'll extract posts directly
                articles = await page.query_selector_all('article')

                for i, article in enumerate(articles[:10]):  # Check first 10 posts
                    try:
                        # Extract post ID
                        link = await article.query_selector('a[href*="/status/"]')
                        if not link:
                            continue

                        href = await link.get_attribute('href')
                        if not href:
                            continue

                        post_id = href.split('/status/')[-1].split('?')[0]

                        if post_id not in displayed_posts:
                            displayed_posts.add(post_id)
                            self.post_count += 1

                            # Extract details
                            user_elem = await article.query_selector('[data-testid="User-Name"]')
                            tweet_elem = await article.query_selector('[data-testid="tweetText"]')

                            handle = 'unknown'
                            content = 'No content'

                            if user_elem:
                                handle_link = await user_elem.query_selector('a[href^="/"]')
                                if handle_link:
                                    handle_href = await handle_link.get_attribute('href')
                                    if handle_href:
                                        handle = handle_href.split('/')[-1]

                            if tweet_elem:
                                content = await tweet_elem.text_content()

                            # Display the post
                            print(f"\n{'=' * 70}")
                            print(f"🔴 LIVE POST #{self.post_count}")
                            print(f"{'=' * 70}")
                            print(f"👤 @{handle}")
                            print(f"💬 {content[:200]}")
                            print(f"🔗 https://x.com/{handle}/status/{post_id}")
                            print(f"{'=' * 70}")

                    except Exception as e:
                        continue

            # Monitoring loop
            while asyncio.get_event_loop().time() - start_time < duration_seconds:
                await asyncio.sleep(2)

                # Check for new posts
                await check_for_posts()

                # Scroll every 10 seconds
                if asyncio.get_event_loop().time() - last_scroll > 10:
                    await page.evaluate("window.scrollBy(0, 500)")
                    print(f"   📜 Scrolling... [{int(asyncio.get_event_loop().time() - start_time)}/{duration_seconds}s]")
                    last_scroll = asyncio.get_event_loop().time()

            # Final summary
            print(f"\n{'=' * 70}")
            print(f"📊 MONITORING COMPLETE")
            print(f"{'=' * 70}")
            print(f"✅ Total unique posts seen: {len(displayed_posts)}")
            print(f"⏱️ Duration: {duration_seconds} seconds")
            print(f"{'=' * 70}")

            await browser.close()

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()

        return self.post_count


async def main():
    """Run the live monitor."""
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    monitor = WorkingLiveMonitor()
    count = await monitor.monitor_posts(duration_seconds=duration)

    if count > 0:
        print(f"\n✅ Successfully monitored {count} posts!")
    else:
        print(f"\n⚠️ No new posts detected during monitoring period")


if __name__ == "__main__":
    asyncio.run(main())
