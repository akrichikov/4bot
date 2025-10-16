#!/usr/bin/env python3
"""
CZ Notification Monitor - Autonomous Mention Detection
Monitors Twitter/X notifications for @4botbsc mentions and triggers auto-replies
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page
from rabbitmq_manager import RabbitMQManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('CZ-NOTIF-MONITOR')


class NotificationMonitor:
    """Monitors Twitter/X notifications for @4botbsc mentions"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.rabbitmq = RabbitMQManager()
        self.rabbitmq.connect()
        self.storage_state = Path("config/profiles/4botbsc/storageState.json")
        self.seen_notifications = set()  # Track processed notifications
        self.poll_interval = 30  # Check every 30 seconds
        self.running = False

    async def setup_browser(self):
        """Initialize authenticated browser session"""
        logger.info("🌐 Setting up headless browser with authentication...")

        if not self.storage_state.exists():
            logger.error(f"❌ Authentication file not found: {self.storage_state}")
            return False

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            storage_state=str(self.storage_state),
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await self.context.new_page()
        logger.info("✅ Browser ready for notification monitoring")
        return True

    async def fetch_notifications(self):
        """Fetch latest notifications from Twitter/X"""
        try:
            # Navigate to notifications page
            logger.info("📬 Fetching notifications...")
            await self.page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(3000)  # Wait for dynamic content

            # Extract notification data
            notifications = await self.page.evaluate("""
                () => {
                    const notifications = [];

                    // Find all timeline items
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');

                    for (const article of articles) {
                        try {
                            // Extract tweet text
                            const textElement = article.querySelector('[data-testid="tweetText"]');
                            const text = textElement ? textElement.innerText : '';

                            // Extract author
                            const authorElement = article.querySelector('[data-testid="User-Name"]');
                            let author = 'unknown';
                            if (authorElement) {
                                const links = authorElement.querySelectorAll('a[role="link"]');
                                if (links.length > 0) {
                                    const href = links[0].getAttribute('href');
                                    if (href && href.startsWith('/')) {
                                        author = href.substring(1);
                                    }
                                }
                            }

                            // Extract tweet URL
                            const timeElement = article.querySelector('time');
                            let tweetUrl = '';
                            if (timeElement && timeElement.parentElement && timeElement.parentElement.getAttribute('href')) {
                                tweetUrl = 'https://x.com' + timeElement.parentElement.getAttribute('href');
                            }

                            // Extract tweet ID from URL
                            let tweetId = '';
                            if (tweetUrl) {
                                const match = tweetUrl.match(/status\\/(\\d+)/);
                                if (match) {
                                    tweetId = match[1];
                                }
                            }

                            // Only include if we have the essential data
                            if (text && author && tweetUrl) {
                                notifications.push({
                                    author: author,
                                    text: text,
                                    url: tweetUrl,
                                    id: tweetId,
                                    timestamp: new Date().toISOString()
                                });
                            }
                        } catch (e) {
                            console.error('Error parsing notification:', e);
                        }
                    }

                    return notifications;
                }
            """)

            logger.info(f"📋 Found {len(notifications)} mentions")
            return notifications

        except Exception as e:
            logger.error(f"❌ Failed to fetch notifications: {e}")
            return []

    async def process_notification(self, notification):
        """Process a single notification and publish to RabbitMQ if new"""
        notif_id = notification.get('id', '')

        if not notif_id:
            logger.warning("⚠️  Notification missing ID, skipping")
            return False

        # Skip if already seen
        if notif_id in self.seen_notifications:
            return False

        # Mark as seen
        self.seen_notifications.add(notif_id)

        author = notification.get('author', 'unknown')
        text = notification.get('text', '')
        url = notification.get('url', '')

        # Skip our own tweets
        if author.lower() in ['4botbsc', '4bot']:
            logger.info(f"⏭️  Skipping own tweet: {notif_id}")
            return False

        logger.info(f"🆕 New mention from @{author}")
        logger.info(f"   Text: {text[:100]}...")
        logger.info(f"   URL: {url}")

        # Publish to RabbitMQ
        success = self.rabbitmq.publish_cz_reply_request(
            post_url=url,
            post_id=notif_id,
            author_handle=author,
            content=text
        )

        if success:
            logger.info(f"✅ Published CZ reply request for tweet {notif_id}")
            return True
        else:
            logger.error(f"❌ Failed to publish request for tweet {notif_id}")
            return False

    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting notification monitoring loop")
        logger.info(f"   Poll interval: {self.poll_interval} seconds")
        logger.info(f"   Target account: @4botbsc")

        self.running = True
        new_count = 0
        poll_count = 0

        while self.running:
            try:
                poll_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔍 Poll #{poll_count} - Checking for new mentions...")

                # Fetch notifications
                notifications = await self.fetch_notifications()

                # Process each notification
                processed_this_round = 0
                for notification in notifications:
                    if await self.process_notification(notification):
                        processed_this_round += 1
                        new_count += 1

                if processed_this_round > 0:
                    logger.info(f"📊 Processed {processed_this_round} new mentions this round")
                else:
                    logger.info("📊 No new mentions found")

                logger.info(f"📈 Total new mentions since start: {new_count}")
                logger.info(f"💾 Tracking {len(self.seen_notifications)} seen notifications")

                # Wait before next poll
                logger.info(f"⏰ Waiting {self.poll_interval} seconds until next check...")
                await asyncio.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("\n⏹️  Keyboard interrupt received")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in monitor loop: {e}")
                logger.info(f"⏰ Waiting {self.poll_interval} seconds before retry...")
                await asyncio.sleep(self.poll_interval)

    async def run(self):
        """Start the notification monitor"""
        try:
            if not await self.setup_browser():
                logger.error("❌ Failed to setup browser")
                return

            await self.monitor_loop()

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up...")
        if self.browser:
            await self.browser.close()
        if self.rabbitmq:
            self.rabbitmq.close()
        logger.info("✅ Cleanup complete")


async def main():
    """Entry point"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         CZ Notification Monitor - Autonomous Mode            ║")
    print("║                                                              ║")
    print("║  Monitoring @4botbsc mentions and triggering auto-replies   ║")
    print("║                                                              ║")
    print("║  Press Ctrl+C to stop                                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    monitor = NotificationMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
