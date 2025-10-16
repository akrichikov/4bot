#!/usr/bin/env python3
"""
Real-time X/Twitter Notification Monitor
Monitors the notifications page for likes, retweets, replies, mentions, and follows.
Runs in a separate browser instance for isolation.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import Optional, List
from enum import Enum


# Setup dual logging (file + console)
log_file = f'notifications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of X/Twitter notifications."""
    LIKE = "like"
    RETWEET = "retweet"
    REPLY = "reply"
    MENTION = "mention"
    FOLLOW = "follow"
    QUOTE = "quote"
    UNKNOWN = "unknown"


@dataclass
class NotificationEvent:
    """Represents a notification event."""
    id: str
    type: NotificationType
    from_user: str
    from_handle: str
    timestamp: datetime
    content: Optional[str] = None
    post_content: Optional[str] = None
    post_id: Optional[str] = None
    count: int = 1  # For grouped notifications (e.g., "3 people liked")
    raw_text: Optional[str] = None


class NotificationMonitor:
    """Monitors X/Twitter notifications in real-time."""

    def __init__(self):
        self.notifications_seen = set()
        self.notification_count = 0
        self.events: List[NotificationEvent] = []
        self.running = True

    async def process_notification(self, notif_data: dict):
        """Process a notification event."""
        try:
            # Generate unique ID
            notif_id = f"{notif_data.get('type')}_{notif_data.get('from_handle')}_{notif_data.get('timestamp')}"

            if notif_id in self.notifications_seen:
                return

            self.notifications_seen.add(notif_id)
            self.notification_count += 1

            # Determine notification type
            raw_text = notif_data.get('raw_text', '').lower()
            notif_type = NotificationType.UNKNOWN

            if 'liked' in raw_text:
                notif_type = NotificationType.LIKE
            elif 'reposted' in raw_text or 'retweeted' in raw_text:
                notif_type = NotificationType.RETWEET
            elif 'replied' in raw_text:
                notif_type = NotificationType.REPLY
            elif 'mentioned' in raw_text:
                notif_type = NotificationType.MENTION
            elif 'followed' in raw_text:
                notif_type = NotificationType.FOLLOW
            elif 'quoted' in raw_text:
                notif_type = NotificationType.QUOTE

            # Create notification event
            event = NotificationEvent(
                id=notif_id,
                type=notif_type,
                from_user=notif_data.get('from_user', 'Unknown'),
                from_handle=notif_data.get('from_handle', 'unknown'),
                timestamp=datetime.fromisoformat(notif_data.get('timestamp', datetime.now().isoformat())),
                content=notif_data.get('content'),
                post_content=notif_data.get('post_content'),
                post_id=notif_data.get('post_id'),
                raw_text=notif_data.get('raw_text')
            )

            self.events.append(event)

            # Log the notification
            logger.info("=" * 70)
            logger.info(f"🔔 NOTIFICATION #{self.notification_count}")
            logger.info(f"Type: {notif_type.value.upper()}")
            logger.info(f"From: @{event.from_handle} ({event.from_user})")

            if event.content:
                logger.info(f"Content: {event.content[:200]}")

            if event.post_content:
                logger.info(f"Related Post: {event.post_content[:100]}")

            if event.post_id:
                logger.info(f"Post Link: https://x.com/i/status/{event.post_id}")

            logger.info(f"Raw: {event.raw_text[:150] if event.raw_text else 'N/A'}")
            logger.info("=" * 70)

            # Special formatting for different types
            if notif_type == NotificationType.LIKE:
                print(f"❤️  @{event.from_handle} liked your post")
            elif notif_type == NotificationType.RETWEET:
                print(f"🔄 @{event.from_handle} retweeted your post")
            elif notif_type == NotificationType.REPLY:
                print(f"💬 @{event.from_handle} replied: {event.content[:100] if event.content else ''}")
            elif notif_type == NotificationType.FOLLOW:
                print(f"➕ @{event.from_handle} followed you")
            elif notif_type == NotificationType.MENTION:
                print(f"🔔 @{event.from_handle} mentioned you")
            elif notif_type == NotificationType.QUOTE:
                print(f"💭 @{event.from_handle} quoted your post")

        except Exception as e:
            logger.error(f"Error processing notification: {e}")

    async def monitor_notifications(self, duration_seconds=300):
        """Monitor notifications page for specified duration."""

        logger.info("=" * 70)
        logger.info("X/TWITTER NOTIFICATION MONITOR STARTED")
        logger.info(f"Duration: {duration_seconds} seconds")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 70)

        # Load cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        logger.info(f"Loaded {len(cookies)} cookies")

        playwright = await async_playwright().start()

        try:
            # Launch separate browser instance
            logger.info("Launching dedicated browser instance...")
            browser = await playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Console handler for notifications
            def handle_console(msg):
                text = msg.text
                if '__NOTIFICATION__' in text:
                    try:
                        json_str = text.split('__NOTIFICATION__:')[1]
                        notif_data = json.loads(json_str)
                        asyncio.create_task(self.process_notification(notif_data))
                    except Exception as e:
                        logger.error(f"Error parsing notification: {e}")

            page.on("console", handle_console)

            # Navigate to notifications page
            logger.info("Navigating to notifications page...")
            await page.goto('https://x.com/notifications', wait_until='networkidle')
            await asyncio.sleep(3)

            # Check if we're on notifications page
            current_url = page.url
            if 'notifications' not in current_url:
                logger.warning(f"Not on notifications page. Current URL: {current_url}")

            # Inject notification observer
            observer_script = """
            (() => {
                console.log('Injecting notification observer...');
                const seenNotifications = new Set();
                let notifCount = 0;

                function extractNotification(element) {
                    try {
                        // Generate unique identifier
                        const textContent = element.textContent || '';
                        const notifId = btoa(textContent.substring(0, 100));

                        if (seenNotifications.has(notifId)) return null;
                        seenNotifications.add(notifId);
                        notifCount++;

                        // Extract user who triggered notification
                        let fromUser = 'Unknown';
                        let fromHandle = 'unknown';

                        // Look for user links
                        const userLinks = element.querySelectorAll('a[href^="/"]');
                        if (userLinks.length > 0) {
                            // First link is usually the user who triggered the notification
                            const userLink = userLinks[0];
                            fromHandle = userLink.href.split('/').pop() || 'unknown';

                            // Try to get display name
                            const nameElement = userLink.querySelector('span');
                            if (nameElement) {
                                fromUser = nameElement.textContent;
                            }
                        }

                        // Look for user avatar and name
                        const avatarLink = element.querySelector('a[role="link"][href^="/"]');
                        if (avatarLink) {
                            fromHandle = avatarLink.href.split('/').pop() || fromHandle;
                        }

                        // Extract notification text
                        const textElements = element.querySelectorAll('span');
                        let notificationText = '';
                        let postContent = '';

                        textElements.forEach(span => {
                            const text = span.textContent || '';
                            if (text.includes('liked') || text.includes('reposted') ||
                                text.includes('replied') || text.includes('followed') ||
                                text.includes('mentioned') || text.includes('quoted')) {
                                notificationText = text;
                            }
                        });

                        // Try to extract post content if present
                        const postTextElement = element.querySelector('[data-testid="tweetText"]');
                        if (postTextElement) {
                            postContent = postTextElement.textContent;
                        }

                        // Try to extract post ID from any status links
                        let postId = null;
                        const statusLink = element.querySelector('a[href*="/status/"]');
                        if (statusLink) {
                            const href = statusLink.href;
                            const match = href.match(/status\\/(\\d+)/);
                            if (match) {
                                postId = match[1];
                            }
                        }

                        const notificationData = {
                            id: notifId,
                            from_user: fromUser,
                            from_handle: fromHandle,
                            raw_text: notificationText || textContent.substring(0, 200),
                            content: null,  // Will be filled for replies/quotes
                            post_content: postContent,
                            post_id: postId,
                            timestamp: new Date().toISOString()
                        };

                        // For replies, try to get reply content
                        if (notificationText.includes('replied')) {
                            const replyElements = element.querySelectorAll('[data-testid="tweetText"]');
                            if (replyElements.length > 1) {
                                notificationData.content = replyElements[1].textContent;
                            }
                        }

                        console.log('__NOTIFICATION__:' + JSON.stringify(notificationData));
                        return notificationData;

                    } catch (error) {
                        console.error('Error extracting notification:', error);
                        return null;
                    }
                }

                // Process existing notifications
                const existingNotifs = document.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                console.log(`Found ${existingNotifs.length} existing notification elements`);
                existingNotifs.forEach(extractNotification);

                // Monitor for new notifications
                const observer = new MutationObserver((mutations) => {
                    for (const mutation of mutations) {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // Check for notification containers
                                const articles = node.tagName === 'ARTICLE' ? [node] :
                                               (node.querySelectorAll ? node.querySelectorAll('article, [data-testid="cellInnerDiv"]') : []);

                                articles.forEach(article => {
                                    extractNotification(article);
                                });
                            }
                        }
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                console.log('Notification observer active. Monitoring for notifications...');
                return notifCount;
            })();
            """

            initial_count = await page.evaluate(observer_script)
            logger.info(f"Observer injected. Found {initial_count} initial notifications")

            # Monitor for specified duration
            start_time = asyncio.get_event_loop().time()
            last_refresh = 0

            logger.info("Monitoring notifications...")
            print("\n📡 Waiting for notifications...\n")

            while self.running and (asyncio.get_event_loop().time() - start_time < duration_seconds):
                await asyncio.sleep(1)

                # Refresh every 30 seconds to catch new notifications
                if asyncio.get_event_loop().time() - last_refresh > 30:
                    logger.info(f"Refreshing... [{int(asyncio.get_event_loop().time() - start_time)}s elapsed]")
                    await page.reload()
                    await asyncio.sleep(3)
                    await page.evaluate(observer_script)
                    last_refresh = asyncio.get_event_loop().time()

            # Summary
            logger.info("=" * 70)
            logger.info("MONITORING SUMMARY")
            logger.info(f"Total notifications: {self.notification_count}")

            # Count by type
            type_counts = {}
            for event in self.events:
                type_counts[event.type.value] = type_counts.get(event.type.value, 0) + 1

            logger.info("Notifications by type:")
            for notif_type, count in type_counts.items():
                logger.info(f"  {notif_type}: {count}")

            # Save all notifications to JSON
            output_file = f'notifications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w') as f:
                json.dump([asdict(e) for e in self.events], f, indent=2, default=str)

            logger.info(f"Notifications saved to: {output_file}")
            logger.info("=" * 70)

            await browser.close()

        except Exception as e:
            logger.error(f"Monitor error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()


async def main():
    """Run the notification monitor."""
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 120  # Default 2 minutes

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║              X/TWITTER NOTIFICATION MONITOR                      ║
    ║                                                                  ║
    ║  Monitoring: Likes, Retweets, Replies, Mentions, Follows        ║
    ║  Account: akrichikov@gmail.com (test)                           ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    monitor = NotificationMonitor()
    await monitor.monitor_notifications(duration_seconds=duration)

    print(f"\n✅ Monitoring complete. Detected {monitor.notification_count} notifications")


if __name__ == "__main__":
    asyncio.run(main())