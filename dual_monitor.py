#!/usr/bin/env python3
"""
Dual Monitor System - Runs both feed and notification monitoring simultaneously
Uses separate browser instances for complete isolation.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import sys


# Setup logging
log_dir = Path("dual_monitor_logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Configure loggers for each monitor
feed_logger = logging.getLogger('feed_monitor')
feed_handler = logging.FileHandler(log_dir / f'feed_{timestamp}.log')
feed_handler.setFormatter(logging.Formatter('%(asctime)s | FEED | %(message)s'))
feed_logger.addHandler(feed_handler)
feed_logger.setLevel(logging.INFO)

notif_logger = logging.getLogger('notif_monitor')
notif_handler = logging.FileHandler(log_dir / f'notifications_{timestamp}.log')
notif_handler.setFormatter(logging.Formatter('%(asctime)s | NOTIF | %(message)s'))
notif_logger.addHandler(notif_handler)
notif_logger.setLevel(logging.INFO)

# Console output
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S'))
console.setLevel(logging.INFO)

main_logger = logging.getLogger('main')
main_logger.addHandler(console)
main_logger.setLevel(logging.INFO)


class DualMonitor:
    """Runs both feed and notification monitoring simultaneously."""

    def __init__(self):
        self.feed_posts = []
        self.notifications = []
        self.feed_count = 0
        self.notif_count = 0
        self.running = True

    async def monitor_feed(self, page, duration):
        """Monitor the main feed for posts."""
        feed_logger.info("Starting feed monitor")
        main_logger.info("📡 FEED: Starting monitor on home feed")

        # Inject feed observer
        feed_observer = """
        (() => {
            const seenPosts = new Set();
            let postCount = 0;

            function extractPost(article) {
                try {
                    const link = article.querySelector('a[href*="/status/"]');
                    if (!link) return;

                    const postId = link.href.split('/status/')[1]?.split('?')[0];
                    if (!postId || seenPosts.has(postId)) return;

                    seenPosts.add(postId);
                    postCount++;

                    // Extract author
                    const userElement = article.querySelector('[data-testid="User-Name"]');
                    let authorHandle = 'unknown';
                    if (userElement) {
                        const handleLink = userElement.querySelector('a[href^="/"]');
                        if (handleLink) {
                            authorHandle = handleLink.href.split('/').pop();
                        }
                    }

                    // Extract content
                    const tweetText = article.querySelector('[data-testid="tweetText"]');
                    const content = tweetText ? tweetText.textContent : '';

                    // Extract metrics
                    const likeBtn = article.querySelector('[data-testid="like"],[data-testid="unlike"]');
                    const likes = likeBtn?.querySelector('span')?.textContent || '0';

                    console.log('__FEED_POST__:' + JSON.stringify({
                        id: postId,
                        handle: authorHandle,
                        content: content.substring(0, 200),
                        likes: likes,
                        timestamp: new Date().toISOString()
                    }));
                } catch (error) {
                    // Silent
                }
            }

            // Process existing
            document.querySelectorAll('article').forEach(extractPost);

            // Monitor new
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.querySelectorAll) {
                            node.querySelectorAll('article').forEach(extractPost);
                        }
                    });
                });
            });

            observer.observe(document.body, { childList: true, subtree: true });
            console.log('Feed observer active. Posts found: ' + postCount);
            return postCount;
        })();
        """

        # Console handler for feed
        def handle_feed_console(msg):
            text = msg.text
            if '__FEED_POST__' in text:
                try:
                    data = json.loads(text.split('__FEED_POST__:')[1])
                    self.feed_count += 1
                    self.feed_posts.append(data)

                    content = data['content'][:100]
                    main_logger.info(f"📝 FEED POST #{self.feed_count}: @{data['handle']}: {content}")
                    feed_logger.info(f"Post from @{data['handle']}: {data['content']}")
                except:
                    pass

        page.on("console", handle_feed_console)

        # Navigate to home feed
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Inject observer
        initial = await page.evaluate(feed_observer)
        main_logger.info(f"📡 FEED: Observer active, {initial} initial posts")

        # Monitor and scroll
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < duration:
            await asyncio.sleep(10)
            await page.evaluate("window.scrollBy(0, 500)")
            feed_logger.info(f"Scrolling... {self.feed_count} posts captured")

        feed_logger.info(f"Feed monitoring complete. Total posts: {self.feed_count}")

    async def monitor_notifications(self, page, duration):
        """Monitor the notifications page."""
        notif_logger.info("Starting notification monitor")
        main_logger.info("🔔 NOTIF: Starting monitor on notifications")

        # Inject notification observer
        notif_observer = """
        (() => {
            const seenNotifications = new Set();
            let notifCount = 0;

            function extractNotification(element) {
                try {
                    const textContent = element.textContent || '';
                    const notifId = btoa(textContent.substring(0, 100));

                    if (seenNotifications.has(notifId)) return;
                    seenNotifications.add(notifId);
                    notifCount++;

                    // Extract user
                    let fromHandle = 'unknown';
                    const userLinks = element.querySelectorAll('a[href^="/"]');
                    if (userLinks.length > 0) {
                        fromHandle = userLinks[0].href.split('/').pop() || 'unknown';
                    }

                    // Determine type
                    let type = 'unknown';
                    const text = textContent.toLowerCase();
                    if (text.includes('liked')) type = 'like';
                    else if (text.includes('reposted')) type = 'retweet';
                    else if (text.includes('replied')) type = 'reply';
                    else if (text.includes('followed')) type = 'follow';
                    else if (text.includes('mentioned')) type = 'mention';

                    console.log('__NOTIFICATION__:' + JSON.stringify({
                        type: type,
                        from_handle: fromHandle,
                        text: textContent.substring(0, 200),
                        timestamp: new Date().toISOString()
                    }));
                } catch (error) {
                    // Silent
                }
            }

            // Process existing
            document.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractNotification);

            // Monitor new
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.querySelectorAll) {
                            node.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractNotification);
                        }
                    });
                });
            });

            observer.observe(document.body, { childList: true, subtree: true });
            console.log('Notification observer active. Notifications found: ' + notifCount);
            return notifCount;
        })();
        """

        # Console handler for notifications
        def handle_notif_console(msg):
            text = msg.text
            if '__NOTIFICATION__' in text:
                try:
                    data = json.loads(text.split('__NOTIFICATION__:')[1])
                    self.notif_count += 1
                    self.notifications.append(data)

                    emoji = {'like': '❤️', 'retweet': '🔄', 'reply': '💬',
                            'follow': '➕', 'mention': '🔔'}.get(data['type'], '📌')

                    main_logger.info(f"{emoji} NOTIF #{self.notif_count}: {data['type']} from @{data['from_handle']}")
                    notif_logger.info(f"{data['type']} from @{data['from_handle']}: {data['text'][:100]}")
                except:
                    pass

        page.on("console", handle_notif_console)

        # Navigate to notifications
        await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Inject observer
        initial = await page.evaluate(notif_observer)
        main_logger.info(f"🔔 NOTIF: Observer active, {initial} initial notifications")

        # Monitor with periodic refresh
        start = asyncio.get_event_loop().time()
        last_refresh = 0
        while asyncio.get_event_loop().time() - start < duration:
            await asyncio.sleep(10)

            # Refresh notifications page every 30 seconds
            if asyncio.get_event_loop().time() - last_refresh > 30:
                await page.reload()
                await asyncio.sleep(3)
                await page.evaluate(notif_observer)
                notif_logger.info(f"Refreshed. {self.notif_count} notifications captured")
                last_refresh = asyncio.get_event_loop().time()

        notif_logger.info(f"Notification monitoring complete. Total: {self.notif_count}")

    async def run_dual_monitors(self, duration_seconds=120):
        """Run both monitors simultaneously in separate browser instances."""

        main_logger.info("=" * 70)
        main_logger.info("DUAL MONITOR SYSTEM STARTING")
        main_logger.info(f"Duration: {duration_seconds} seconds")
        main_logger.info(f"Logs: {log_dir}")
        main_logger.info("=" * 70)

        # Load cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        playwright = await async_playwright().start()

        try:
            # Launch TWO separate browser instances
            main_logger.info("🚀 Launching browser instance #1 (Feed Monitor)...")
            browser1 = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            main_logger.info("🚀 Launching browser instance #2 (Notification Monitor)...")
            browser2 = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            # Create contexts with cookies
            context1 = await browser1.new_context(viewport={'width': 1920, 'height': 1080})
            await context1.add_cookies(cookies)
            page1 = await context1.new_page()

            context2 = await browser2.new_context(viewport={'width': 1920, 'height': 1080})
            await context2.add_cookies(cookies)
            page2 = await context2.new_page()

            main_logger.info("✅ Both browser instances ready")
            main_logger.info("🎯 Starting dual monitoring...")

            # Run both monitors concurrently
            await asyncio.gather(
                self.monitor_feed(page1, duration_seconds),
                self.monitor_notifications(page2, duration_seconds)
            )

            # Summary
            main_logger.info("=" * 70)
            main_logger.info("DUAL MONITORING COMPLETE")
            main_logger.info(f"📝 Feed posts captured: {self.feed_count}")
            main_logger.info(f"🔔 Notifications captured: {self.notif_count}")

            # Count notification types
            notif_types = {}
            for n in self.notifications:
                notif_types[n['type']] = notif_types.get(n['type'], 0) + 1

            main_logger.info("Notification breakdown:")
            for ntype, count in notif_types.items():
                main_logger.info(f"  {ntype}: {count}")

            # Save combined report
            report = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration_seconds,
                'feed': {
                    'count': self.feed_count,
                    'posts': self.feed_posts
                },
                'notifications': {
                    'count': self.notif_count,
                    'types': notif_types,
                    'events': self.notifications
                }
            }

            report_file = log_dir / f'dual_monitor_report_{timestamp}.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            main_logger.info(f"📊 Report saved: {report_file}")
            main_logger.info("=" * 70)

            await browser1.close()
            await browser2.close()

        except Exception as e:
            main_logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()


async def main():
    """Main entry point."""
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║              DUAL MONITOR SYSTEM                                 ║
    ║                                                                  ║
    ║  Instance 1: Feed Monitor (Home Timeline)                       ║
    ║  Instance 2: Notification Monitor (Likes/Retweets/Replies)      ║
    ║                                                                  ║
    ║  Running in parallel with complete isolation                    ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    monitor = DualMonitor()
    await monitor.run_dual_monitors(duration_seconds=duration)


if __name__ == "__main__":
    asyncio.run(main())