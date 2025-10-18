#!/usr/bin/env python3
"""
CZ Notification Daemon - Complete Pipeline
Monitors notifications → Filters @4botbsc mentions → VTerm CZ reply → RabbitMQ → Post reply
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pika
import threading
from queue import Queue

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
from xbot.cookies import load_cookie_json, merge_into_storage
from playwright.async_api import Page
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage
from vterm_cz_integration import CZPersonaVTerm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-DAEMON] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_daemon')


@dataclass
class NotificationEvent:
    """Parsed notification event"""
    id: str
    type: str  # mention, reply, retweet, like, follow
    author: str
    author_handle: str
    content: str
    url: str
    timestamp: str

    def is_mention_of_4botbsc(self) -> bool:
        """Check if this notification mentions @4botbsc"""
        content_lower = self.content.lower() if self.content else ""
        return '@4botbsc' in content_lower or '4botbsc' in self.author_handle.lower()


class NotificationMonitor:
    """Monitors X/Twitter notifications in headless mode"""

    def __init__(self, page: Page):
        self.page = page
        self.processed_ids = set()

    async def get_notifications(self) -> List[NotificationEvent]:
        """Extract notifications from the page"""
        script = """
        () => {
            const notifications = [];
            const articles = document.querySelectorAll('article[data-testid="tweet"]');

            articles.forEach(article => {
                try {
                    // Extract notification type from parent
                    const parentDiv = article.closest('[data-testid*="cell"]');
                    let notifType = 'mention';

                    // Check for notification type indicators
                    const svgPath = parentDiv?.querySelector('svg path');
                    if (svgPath) {
                        const d = svgPath.getAttribute('d');
                        if (d && d.includes('M3.75')) notifType = 'like';
                        else if (d && d.includes('M4.5')) notifType = 'retweet';
                        else if (d && d.includes('M1.751')) notifType = 'reply';
                    }

                    // Get text content
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.textContent : '';

                    // Get author
                    const links = article.querySelectorAll('a[href^="/"]');
                    let author = '';
                    let authorHandle = '';
                    for (const link of links) {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\/[^\/]+$/) && !href.includes('status')) {
                            authorHandle = href.substring(1);
                            // Get display name
                            const nameEl = link.querySelector('[dir="ltr"] > span');
                            author = nameEl ? nameEl.textContent : authorHandle;
                            break;
                        }
                    }

                    // Get URL
                    const statusLink = article.querySelector('a[href*="/status/"]');
                    const url = statusLink ? statusLink.href : '';
                    const id = url ? url.split('/status/')[1]?.split('/')[0] : '';

                    // Skip if no ID
                    if (!id) return;

                    notifications.push({
                        id: id,
                        type: notifType,
                        author: author,
                        author_handle: authorHandle,
                        content: text,
                        url: url,
                        timestamp: new Date().toISOString()
                    });

                } catch (e) {
                    console.error('Error parsing notification:', e);
                }
            });

            return notifications;
        }
        """

        notifications_data = await self.page.evaluate(script)

        # Convert to NotificationEvent objects and filter new ones
        events = []
        for data in notifications_data:
            if data['id'] not in self.processed_ids:
                event = NotificationEvent(**data)
                # Filter for @4botbsc mentions only
                if event.is_mention_of_4botbsc():
                    events.append(event)
                    self.processed_ids.add(data['id'])
                    logger.info(f"📥 New @4botbsc mention from @{event.author_handle}: {event.content[:50]}...")

        return events


class VTermCZProcessor:
    """Processes notifications through VTerm to generate CZ replies"""

    def __init__(self):
        self.cz_vterm = CZPersonaVTerm()

    def generate_reply(self, notification: NotificationEvent) -> Optional[str]:
        """Generate a CZ reply for the notification"""
        context = {
            "type": "notification",
            "notification_type": notification.type,
            "author": notification.author_handle,
            "text": notification.content
        }

        reply = self.cz_vterm.generate_reply(context)
        logger.info(f"🤖 Generated CZ reply: {reply}")
        return reply

    def close(self):
        """Close VTerm connection"""
        self.cz_vterm.close()


class RabbitMQReplyPublisher:
    """Publishes replies to RabbitMQ for posting"""

    def __init__(self):
        self.manager = RabbitMQManager()
        self.manager.connect()

    def publish_reply_request(self, notification: NotificationEvent, reply_text: str) -> bool:
        """Publish a reply request to RabbitMQ"""
        try:
            message = BotMessage(
                message_id=f"reply_{notification.id}_{datetime.now().timestamp()}",
                message_type="reply_request",
                timestamp=datetime.now().isoformat(),
                source="cz_daemon",
                data={
                    "notification_id": notification.id,
                    "reply_to_url": notification.url,
                    "reply_text": reply_text,
                    "original_author": notification.author_handle,
                    "original_content": notification.content
                },
                metadata={
                    "priority": "high" if notification.type == "mention" else "normal",
                    "persona": "CZ"
                }
            )

            # Publish to request queue
            success = self.manager.publish_message(
                message=message,
                routing_key='4bot.request.reply'
            )

            if success:
                logger.info(f"📤 Published reply request to RabbitMQ for @{notification.author_handle}")

            return success

        except Exception as e:
            logger.error(f"❌ Failed to publish reply: {e}")
            return False

    def close(self):
        """Close RabbitMQ connection"""
        self.manager.close()


class CZReplyPoster:
    """Consumes reply requests from RabbitMQ and posts them to X/Twitter"""

    def __init__(self, config: Config):
        self.config = config
        self.bot = XBot(config)
        self.manager = RabbitMQManager()
        self.manager.connect()

    async def post_reply(self, reply_data: Dict[str, Any]) -> bool:
        """Post a reply to X/Twitter"""
        try:
            url = reply_data.get('reply_to_url')
            text = reply_data.get('reply_text')

            if not url or not text:
                logger.error("Missing URL or text in reply data")
                return False

            # Use XBot to post the reply
            await self.bot.reply(url, text)

            logger.info(f"✅ Posted reply: {text[:50]}... to {url}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to post reply: {e}")
            return False

    def process_reply_request(self, message: BotMessage):
        """Process a reply request from RabbitMQ"""
        try:
            # Run async reply posting in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self.post_reply(message.data))
            loop.close()

            # Publish response
            response = BotMessage(
                message_id=f"response_{message.message_id}",
                message_type="reply_response",
                timestamp=datetime.now().isoformat(),
                source="cz_reply_poster",
                data={
                    "request_id": message.message_id,
                    "success": success,
                    "posted_at": datetime.now().isoformat() if success else None
                }
            )

            self.manager.publish_message(
                message=response,
                routing_key='4bot.response.reply'
            )

        except Exception as e:
            logger.error(f"Error processing reply request: {e}")

    def start_consuming(self):
        """Start consuming reply requests"""
        self.manager.register_handler("reply_request", self.process_reply_request)
        logger.info("🎧 Starting reply consumer...")
        self.manager.consume_requests()


class CZNotificationDaemon:
    """Main daemon orchestrating the entire pipeline"""

    def __init__(self):
        self.config = Config.from_env()
        self.config.headless = True
        self.config.persist_session = False

        # Components
        self.monitor = None
        self.vterm_processor = VTermCZProcessor()
        self.rabbitmq_publisher = RabbitMQReplyPublisher()
        self.reply_poster_thread = None

    async def setup_browser(self) -> Browser:
        """Setup headless browser with authentication"""
        # Setup authentication
        from xbot.profiles import profile_paths
        cfg_storage = Path("config/profiles/4botbsc/storageState.json")
        if cfg_storage.exists():
            self.config.storage_state = cfg_storage
            self.config.user_data_dir = Path(".x-user/4botbsc")
        else:
            storage, user_dir = profile_paths("4botbsc")
            self.config.storage_state = storage
            self.config.user_data_dir = user_dir

        # Load cookies
        cookie_path = Path("auth_data/x_cookies.json")
        if cookie_path.exists():
            cookies = load_cookie_json(cookie_path)
            merge_into_storage(
                Path(self.config.storage_state),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info("✅ Authentication configured")

        browser = Browser(self.config, label="cz_notification_daemon")
        return browser

    def start_reply_poster(self):
        """Start the reply poster in a separate thread"""
        def run_poster():
            poster = CZReplyPoster(self.config)
            poster.start_consuming()

        self.reply_poster_thread = threading.Thread(target=run_poster, daemon=True)
        self.reply_poster_thread.start()
        logger.info("🚀 Reply poster thread started")

    async def monitor_loop(self, page: Page):
        """Main monitoring loop"""
        self.monitor = NotificationMonitor(page)

        while True:
            try:
                # Navigate to notifications if not there
                if 'notifications' not in page.url:
                    await page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded")
                    await asyncio.sleep(3)

                # Get new notifications
                notifications = await self.monitor.get_notifications()

                # Process each notification
                for notif in notifications:
                    # Generate CZ reply using VTerm
                    reply = self.vterm_processor.generate_reply(notif)

                    if reply:
                        # Publish to RabbitMQ
                        self.rabbitmq_publisher.publish_reply_request(notif, reply)

                # Check every 30 seconds
                await asyncio.sleep(30)

                # Refresh page occasionally to get new notifications
                if time.time() % 300 < 30:  # Every 5 minutes
                    await page.reload()
                    await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Run the daemon"""
        logger.info("🚀 Starting CZ Notification Daemon")
        logger.info("   Mode: HEADLESS ✅")
        logger.info("   Filter: @4botbsc mentions only ✅")
        logger.info("   Pipeline: Notification → VTerm → RabbitMQ → Post ✅")

        # Start reply poster thread
        self.start_reply_poster()

        async with await self.setup_browser() as browser:
            page = browser.page

            # Login if needed
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            if not await page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]'):
                logger.error("❌ Not logged in - check authentication")
                return

            logger.info("✅ Logged in successfully")

            # Start monitoring
            await self.monitor_loop(page)

    def cleanup(self):
        """Cleanup resources"""
        self.vterm_processor.close()
        self.rabbitmq_publisher.close()
        logger.info("🛑 Daemon stopped")


async def main():
    """Main entry point"""
    daemon = CZNotificationDaemon()

    try:
        await daemon.run()
    except KeyboardInterrupt:
        logger.info("⛔ Daemon stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        daemon.cleanup()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CZ NOTIFICATION DAEMON - ACTIVATED                  ║
║                                                               ║
║  🔔 Monitoring: @4botbsc mentions only                       ║
║  🤖 Reply Gen: VTerm CZ Persona                              ║
║  📨 Queue: RabbitMQ message passing                          ║
║  📤 Posting: Headless browser automation                     ║
║  🔄 Mode: Continuous daemon                                  ║
║                                                               ║
║           Press Ctrl+C to stop                               ║
╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
