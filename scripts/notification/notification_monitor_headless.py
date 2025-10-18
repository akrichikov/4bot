#!/usr/bin/env python3
"""
Headless Notification Monitor - Runs silently in background
Monitors X/Twitter notifications continuously and logs everything.
"""

import asyncio
from typing import Any as _Moved
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from collections import defaultdict
import signal
import sys


# Enhanced logging with multiple handlers
class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'NOTIF': '\033[95m',    # Light Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])

        # Special formatting for notifications
        if hasattr(record, 'notification'):
            return f"{log_color}🔔 {record.getMessage()}{self.COLORS['RESET']}"

        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


# Setup logging
log_dir = Path("notification_logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'notifications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

# File handler - detailed logging
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Console handler - colored output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
))

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class HeadlessNotificationMonitor:
    """Headless notification monitor for continuous operation."""

    def __init__(self):
        self.running = True
        self.stats = defaultdict(int)
        self.notifications = []
        self.start_time = None
        self.browser = None
        self.context = None
        self.page = None

        # Handle shutdown signals
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown gracefully."""
        logger.info("Shutdown signal received. Stopping monitor...")
        self.running = False

    async def process_notification(self, data):
        """Process incoming notification data."""
        try:
            # Determine notification type
            text = data.get('raw_text', '').lower()
            notif_type = 'unknown'

            if 'liked your' in text or 'liked a post' in text:
                notif_type = 'like'
                emoji = '❤️'
            elif 'reposted' in text or 'retweeted' in text:
                notif_type = 'retweet'
                emoji = '🔄'
            elif 'replied to' in text:
                notif_type = 'reply'
                emoji = '💬'
            elif 'mentioned you' in text:
                notif_type = 'mention'
                emoji = '🔔'
            elif 'followed you' in text:
                notif_type = 'follow'
                emoji = '➕'
            elif 'quoted your' in text:
                notif_type = 'quote'
                emoji = '💭'
            else:
                emoji = '📌'

            # Update stats
            self.stats[notif_type] += 1
            self.stats['total'] += 1

            # Store notification
            notification = {
                'type': notif_type,
                'from_user': data.get('from_user', 'Unknown'),
                'from_handle': data.get('from_handle', 'unknown'),
                'content': data.get('content'),
                'post_content': data.get('post_content'),
                'post_id': data.get('post_id'),
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'raw_text': data.get('raw_text')
            }
            self.notifications.append(notification)

            # Log notification with special marker
            log_msg = f"{emoji} {notif_type.upper()}: @{notification['from_handle']}"
            if notification.get('content'):
                log_msg += f" - {notification['content'][:100]}"

            logger.info(log_msg, extra={'notification': True})

            # Log to file with full details
            logger.debug(f"Full notification data: {json.dumps(notification, default=str)}")

            # Print live stats every 10 notifications
            if self.stats['total'] % 10 == 0:
                self._print_stats()

        except Exception as e:
            logger.error(f"Error processing notification: {e}")

    def _print_stats(self):
        """Print current statistics."""
        elapsed = int((datetime.now() - self.start_time).total_seconds())
        logger.info("=" * 60)
        logger.info(f"📊 STATS | Runtime: {elapsed}s | Total: {self.stats['total']}")

        for notif_type in ['like', 'retweet', 'reply', 'mention', 'follow', 'quote']:
            if self.stats[notif_type] > 0:
                logger.info(f"  {notif_type.capitalize()}: {self.stats[notif_type]}")

        rate = self.stats['total'] / max(elapsed, 1)
        logger.info(f"  Rate: {rate:.2f} notifications/second")
        logger.info("=" * 60)

    async def start_monitor(self, duration_seconds=None):
        """Start the headless notification monitor."""
        self.start_time = datetime.now()

        logger.info("=" * 70)
        logger.info("HEADLESS NOTIFICATION MONITOR STARTING")
        logger.info(f"Log file: {log_file}")
        logger.info(f"Duration: {'Continuous' if duration_seconds is None else f'{duration_seconds}s'}")
        logger.info("=" * 70)

        # Load cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        if not cookie_file.exists():
            logger.error(f"Cookie file not found: {cookie_file}")
            return

        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        logger.info(f"Loaded {len(cookies)} cookies")

        playwright = await async_playwright().start()

        try:
            # Launch headless browser
            logger.info("Launching headless browser...")
            self.browser = await playwright.chromium.launch(
                headless=True,  # Running headless
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )

            await self.context.add_cookies(cookies)
            self.page = await self.context.new_page()

            # Console handler
            async def handle_console(msg):
                text = msg.text
                if '__NOTIFICATION__' in text:
                    try:
                        json_str = text.split('__NOTIFICATION__:')[1]
                        data = json.loads(json_str)
                        await self.process_notification(data)
                    except Exception as e:
                        logger.debug(f"Console parse error: {e}")

            self.page.on("console", lambda msg: asyncio.create_task(handle_console(msg)))

            # Navigate to notifications
            logger.info("Navigating to notifications page...")
            try:
                await self.page.goto('https://x.com/notifications', wait_until='domcontentloaded', timeout=30000)
            except Exception as e:
                logger.warning(f"Navigation warning: {e}")

            await asyncio.sleep(3)

            # Inject observer script
            observer_script = """
            (() => {
                const seenNotifications = new Set();

                function extractNotification(element) {
                    try {
                        const textContent = element.textContent || '';
                        const notifId = btoa(textContent.substring(0, 100));

                        if (seenNotifications.has(notifId)) return;
                        seenNotifications.add(notifId);

                        // Extract basic info
                        let fromHandle = 'unknown';
                        const userLinks = element.querySelectorAll('a[href^="/"]');
                        if (userLinks.length > 0) {
                            fromHandle = userLinks[0].href.split('/').pop() || 'unknown';
                        }

                        // Get notification text
                        const spans = element.querySelectorAll('span');
                        let notificationText = '';
                        spans.forEach(span => {
                            const text = span.textContent || '';
                            if (text.includes('liked') || text.includes('reposted') ||
                                text.includes('replied') || text.includes('followed') ||
                                text.includes('mentioned') || text.includes('quoted')) {
                                notificationText = text;
                            }
                        });

                        // Get post content if available
                        const postTextElement = element.querySelector('[data-testid="tweetText"]');
                        const postContent = postTextElement ? postTextElement.textContent : null;

                        // Get post ID if available
                        let postId = null;
                        const statusLink = element.querySelector('a[href*="/status/"]');
                        if (statusLink) {
                            const match = statusLink.href.match(/status\\/(\\d+)/);
                            if (match) postId = match[1];
                        }

                        const data = {
                            from_handle: fromHandle,
                            raw_text: notificationText || textContent.substring(0, 200),
                            post_content: postContent,
                            post_id: postId,
                            timestamp: new Date().toISOString()
                        };

                        console.log('__NOTIFICATION__:' + JSON.stringify(data));
                    } catch (error) {
                        // Silent fail
                    }
                }

                // Process existing
                document.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractNotification);

                // Monitor for new
                const observer = new MutationObserver(mutations => {
                    mutations.forEach(mutation => {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const articles = node.querySelectorAll ?
                                    node.querySelectorAll('article, [data-testid="cellInnerDiv"]') : [];
                                articles.forEach(extractNotification);
                            }
                        });
                    });
                });

                observer.observe(document.body, { childList: true, subtree: true });
                return 'Observer active';
            })();
            """

            result = await self.page.evaluate(observer_script)
            logger.info(f"Observer status: {result}")

            logger.info("🟢 MONITOR ACTIVE - Watching for notifications...")
            print("\n" + "=" * 70)
            print("NOTIFICATIONS WILL APPEAR BELOW AS THEY ARRIVE:")
            print("=" * 70 + "\n")

            # Main monitoring loop
            start_time = asyncio.get_event_loop().time()
            last_refresh = 0
            last_stats = 0

            while self.running:
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                # Check duration limit
                if duration_seconds and elapsed > duration_seconds:
                    logger.info("Duration limit reached. Stopping...")
                    break

                # Refresh page periodically
                if current_time - last_refresh > 60:  # Every minute
                    logger.debug("Refreshing page...")
                    await self.page.reload()
                    await asyncio.sleep(3)
                    await self.page.evaluate(observer_script)
                    last_refresh = current_time

                # Print stats periodically
                if current_time - last_stats > 30:  # Every 30 seconds
                    self._print_stats()
                    last_stats = current_time

                await asyncio.sleep(1)

            # Final summary
            self._print_final_summary()

        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)

        finally:
            if self.browser:
                await self.browser.close()
            await playwright.stop()

    def _print_final_summary(self):
        """Print final summary."""
        elapsed = int((datetime.now() - self.start_time).total_seconds())

        logger.info("=" * 70)
        logger.info("MONITORING COMPLETE")
        logger.info(f"Total runtime: {elapsed} seconds")
        logger.info(f"Total notifications: {self.stats['total']}")

        # Breakdown by type
        logger.info("\nNotification breakdown:")
        for notif_type in ['like', 'retweet', 'reply', 'mention', 'follow', 'quote', 'unknown']:
            count = self.stats.get(notif_type, 0)
            if count > 0:
                percentage = (count / max(self.stats['total'], 1)) * 100
                logger.info(f"  {notif_type.capitalize()}: {count} ({percentage:.1f}%)")

        # Save detailed report
        report_file = log_dir / f'notification_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': elapsed,
            'statistics': dict(self.stats),
            'notifications': self.notifications
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"\nDetailed report saved: {report_file}")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 70)


async def main():
    """Main entry point."""
    duration = None
    if len(sys.argv) > 1:
        if sys.argv[1] != 'continuous':
            duration = int(sys.argv[1])

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║          HEADLESS X/TWITTER NOTIFICATION MONITOR                 ║
    ║                                                                  ║
    ║  Running in background mode (headless)                          ║
    ║  Press Ctrl+C to stop monitoring                                ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    monitor = HeadlessNotificationMonitor()
    await monitor.start_monitor(duration_seconds=duration)


if __name__ == "__main__":
    # Usage: python notification_monitor_headless.py [duration|continuous]
    # Examples:
    #   python notification_monitor_headless.py 300        # Run for 5 minutes
    #   python notification_monitor_headless.py continuous # Run indefinitely
    asyncio.run(main())
