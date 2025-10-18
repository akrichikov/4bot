#!/usr/bin/env python3
"""
4Bot Orchestrator - Unified In-Memory Headless Bot
Monitors posts and notifications, generates CZ-persona replies using vterm
"""

import asyncio
from typing import Any as _Moved
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging
import signal

# Add xbot to path
try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from playwright.async_api import async_playwright, Page, Browser
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage, NotificationPublisher, CommandConsumer
from xbot.vterm import VTerm, VTermResult
from xbot.config import Config
from xbot.browser import Browser as XBotBrowser
from xbot.cookies import merge_into_storage, load_cookies_best_effort
from xbot.profiles import storage_state_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('4bot_orchestrator')


@dataclass
class BotConfig:
    """Configuration for 4Bot"""
    profile_name: str = "4botbsc"
    x_user: str = "4botbsc@gmail.com"
    headless: bool = True
    monitor_interval: int = 30  # seconds
    reply_probability: float = 0.3  # 30% chance to reply
    max_replies_per_hour: int = 10
    cz_prompt_path: str = "CLAUDE.md"
    cookies_path: str = "auth_data/x_cookies.json"
    storage_state_path: str = str(storage_state_path("4botbsc"))
    user_data_dir: str = ".x-user/4botbsc"


class PostsMonitor:
    """Monitors timeline posts for engagement opportunities"""

    def __init__(self, page: Page, rabbitmq: RabbitMQManager):
        self.page = page
        self.rabbitmq = rabbitmq
        self.seen_posts = set()
        self.monitoring = False

    async def start_monitoring(self):
        """Start monitoring timeline posts"""
        self.monitoring = True
        logger.info("📱 Starting posts monitoring...")

        # Inject monitoring script
        await self.inject_monitor_script()

        # Set up console message handler
        self.page.on("console", lambda msg: asyncio.create_task(self.handle_console_message(msg)))

    async def inject_monitor_script(self):
        """Inject JavaScript to monitor timeline posts"""
        monitor_script = """
        (() => {
            console.log('🎯 Posts monitor injected');
            const seenPosts = new Set();

            function extractPostData(article) {
                try {
                    // Extract post text
                    const textElement = article.querySelector('[data-testid="tweetText"]');
                    const text = textElement ? textElement.textContent : '';

                    // Extract author
                    const authorLink = article.querySelector('a[role="link"][href^="/"]');
                    const author = authorLink ? authorLink.getAttribute('href').split('/').pop() : 'unknown';

                    // Extract post ID from link
                    const postLink = article.querySelector('a[href*="/status/"]');
                    const postId = postLink ? postLink.href.split('/status/')[1] : null;

                    // Generate unique ID
                    const uniqueId = postId || `${author}_${Date.now()}`;

                    if (!seenPosts.has(uniqueId)) {
                        seenPosts.add(uniqueId);

                        const postData = {
                            id: uniqueId,
                            author: author,
                            text: text.substring(0, 500),
                            timestamp: new Date().toISOString(),
                            type: 'timeline_post'
                        };

                        console.log('__POST_JSON__:' + JSON.stringify(postData));
                    }
                } catch (e) {
                    console.error('Failed to extract post:', e);
                }
            }

            // Monitor existing and new posts
            setInterval(() => {
                const posts = document.querySelectorAll('article[data-testid="tweet"]');
                posts.forEach(extractPostData);
            }, 5000);

            // Clean old posts from memory
            setInterval(() => {
                if (seenPosts.size > 1000) {
                    const toDelete = Array.from(seenPosts).slice(0, 500);
                    toDelete.forEach(id => seenPosts.delete(id));
                }
            }, 60000);
        })();
        """

        await self.page.evaluate(monitor_script)

    async def handle_console_message(self, msg):
        """Handle console messages from injected script"""
        try:
            text = msg.text
            if '__POST_JSON__:' in text:
                json_str = text.split('__POST_JSON__:')[1]
                post_data = json.loads(json_str)

                # Publish to RabbitMQ
                message = BotMessage(
                    message_id=f"post_{post_data['id']}",
                    message_type="timeline_post",
                    timestamp=datetime.now().isoformat(),
                    source="posts_monitor",
                    data=post_data
                )

                self.rabbitmq.publish_message(
                    message=message,
                    routing_key="4bot.response.post"
                )

                logger.info(f"📝 Captured post from @{post_data['author']}")

        except Exception as e:
            logger.error(f"Error handling console message: {e}")

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        logger.info("⏹️ Stopped posts monitoring")


class NotificationsMonitor:
    """Monitors notifications for mentions and interactions"""

    def __init__(self, page: Page, rabbitmq: RabbitMQManager):
        self.page = page
        self.rabbitmq = rabbitmq
        self.seen_notifications = set()
        self.monitoring = False

    async def start_monitoring(self):
        """Start monitoring notifications"""
        self.monitoring = True
        logger.info("🔔 Starting notifications monitoring...")

        # Navigate to notifications page
        await self.page.goto("https://x.com/notifications", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Inject monitoring script
        await self.inject_monitor_script()

        # Set up console message handler
        self.page.on("console", lambda msg: asyncio.create_task(self.handle_console_message(msg)))

    async def inject_monitor_script(self):
        """Inject JavaScript to monitor notifications"""
        monitor_script = """
        (() => {
            console.log('🔔 Notifications monitor injected');
            const seenNotifs = new Set();

            function generateId(text) {
                let hash = 0;
                for (let i = 0; i < Math.min(text.length, 200); i++) {
                    const char = text.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash = hash & hash;
                }
                return `notif_${Math.abs(hash)}_${Date.now()}`;
            }

            function extractNotificationData(element) {
                try {
                    const text = element.textContent || '';
                    const notifId = generateId(text);

                    if (!seenNotifs.has(notifId)) {
                        seenNotifs.add(notifId);

                        // Detect notification type
                        let type = 'unknown';
                        const textLower = text.toLowerCase();
                        if (textLower.includes('liked')) type = 'like';
                        else if (textLower.includes('followed')) type = 'follow';
                        else if (textLower.includes('replied')) type = 'reply';
                        else if (textLower.includes('mentioned')) type = 'mention';
                        else if (textLower.includes('retweeted') || textLower.includes('reposted')) type = 'retweet';

                        // Extract user handle
                        const userLink = element.querySelector('a[href^="/"][role="link"]');
                        const handle = userLink ? userLink.getAttribute('href').split('/').pop() : 'unknown';

                        const notifData = {
                            id: notifId,
                            type: type,
                            from_handle: handle,
                            text: text.substring(0, 500),
                            timestamp: new Date().toISOString()
                        };

                        console.log('__NOTIF_JSON__:' + JSON.stringify(notifData));
                    }
                } catch (e) {
                    console.error('Failed to extract notification:', e);
                }
            }

            // Monitor notifications
            setInterval(() => {
                const notifElements = document.querySelectorAll('[data-testid="cellInnerDiv"]');
                notifElements.forEach(extractNotificationData);
            }, 5000);

            // Auto-refresh every 30 seconds
            setInterval(() => {
                console.log('Refreshing notifications...');
                location.reload();
            }, 30000);
        })();
        """

        await self.page.evaluate(monitor_script)

    async def handle_console_message(self, msg):
        """Handle console messages from injected script"""
        try:
            text = msg.text
            if '__NOTIF_JSON__:' in text:
                json_str = text.split('__NOTIF_JSON__:')[1]
                notif_data = json.loads(json_str)

                # Publish to RabbitMQ
                message = BotMessage(
                    message_id=notif_data['id'],
                    message_type="notification",
                    timestamp=datetime.now().isoformat(),
                    source="notifications_monitor",
                    data=notif_data
                )

                self.rabbitmq.publish_message(
                    message=message,
                    routing_key="4bot.response.notification"
                )

                logger.info(f"🔔 Captured {notif_data['type']} from @{notif_data['from_handle']}")

        except Exception as e:
            logger.error(f"Error handling notification: {e}")

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        logger.info("⏹️ Stopped notifications monitoring")


class VTermReplyGenerator:
    """Generates replies using VTerm with CZ persona"""

    def __init__(self, config: BotConfig):
        self.config = config
        self.vterm = VTerm()
        self.cz_prompt = self._load_cz_prompt()
        self.reply_count = 0
        self.last_reply_time = datetime.now()

    def _load_cz_prompt(self) -> str:
        """Load CZ persona prompt from CLAUDE.md"""
        with open(self.config.cz_prompt_path, 'r') as f:
            return f.read()

    def start(self):
        """Start VTerm"""
        self.vterm.start()
        logger.info("🖥️ VTerm started")

    def generate_reply(self, context: Dict[str, Any]) -> Optional[str]:
        """Generate a reply based on context"""
        # Check rate limiting
        if self.reply_count >= self.config.max_replies_per_hour:
            time_diff = (datetime.now() - self.last_reply_time).seconds
            if time_diff < 3600:  # Within the hour
                logger.warning("Rate limit reached, skipping reply")
                return None

        # Build prompt for reply
        prompt = f"""
        {self.cz_prompt}

        ---

        Context: You are replying to a post on X/Twitter.
        Author: @{context.get('author', 'unknown')}
        Post: {context.get('text', '')}
        Type: {context.get('type', 'post')}

        Generate a short, authentic reply in the CZ persona. Keep it under 280 characters.
        Focus on encouragement, building, and long-term vision.
        If the post is negative or FUD, respond with "4" or pivot to BUIDL.

        Reply:
        """

        # Execute in vterm (simulate LLM response)
        # In production, this would call an actual LLM API
        result = self.vterm.run(f"echo 'Keep building! The future is bright. BUIDL through all market conditions. 🚀'")

        if result.exit_code == 0 and result.raw_text:
            reply = result.raw_text.strip()
            self.reply_count += 1

            # Reset counter every hour
            if (datetime.now() - self.last_reply_time).seconds >= 3600:
                self.reply_count = 1
                self.last_reply_time = datetime.now()

            return reply[:280]  # Ensure under Twitter limit

        return None

    def stop(self):
        """Stop VTerm"""
        self.vterm.close()
        logger.info("🖥️ VTerm stopped")


class FourBotOrchestrator:
    """Main orchestrator for 4Bot"""

    def __init__(self, config: BotConfig):
        self.config = config
        self.browser = None
        self.page = None
        self.rabbitmq = RabbitMQManager()
        self.posts_monitor = None
        self.notifications_monitor = None
        self.reply_generator = VTermReplyGenerator(config)
        self.running = False

    async def setup_browser(self):
        """Setup headless browser with 4botbsc profile"""
        logger.info("🌐 Setting up browser...")

        # Ensure profile directories exist
        os.makedirs(self.config.user_data_dir, exist_ok=True)
        os.makedirs(Path(self.config.storage_state_path).parent, exist_ok=True)

        # Load and merge cookies
        if Path(self.config.cookies_path).exists():
            cookies = load_cookie_json(Path(self.config.cookies_path))
            merge_into_storage(
                Path(self.config.storage_state_path),
                cookies,
                filter_domains=[".x.com", ".twitter.com"]
            )
            logger.info(f"✅ Loaded {len(cookies)} cookies for {self.config.x_user}")

        # Launch browser
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Create context with storage state
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        if Path(self.config.storage_state_path).exists():
            context_options["storage_state"] = self.config.storage_state_path

        context = await self.browser.new_context(**context_options)
        self.page = await context.new_page()

        # Navigate to X.com with improved wait strategy
        try:
            await self.page.goto("https://x.com/home",
                               wait_until="domcontentloaded",
                               timeout=60000)  # 60 second timeout
            await asyncio.sleep(3)
        except Exception as e:
            logger.warning(f"Initial navigation failed: {e}, trying alternative approach...")
            # Try navigating to base URL first
            await self.page.goto("https://x.com",
                               wait_until="domcontentloaded",
                               timeout=60000)
            await asyncio.sleep(5)

        # Check if logged in
        if await self.page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]'):
            logger.info(f"✅ Logged in as {self.config.x_user}")
        else:
            logger.warning("⚠️ Not logged in, may need manual authentication")

    async def setup_monitors(self):
        """Setup posts and notifications monitors"""
        # Setup RabbitMQ
        self.rabbitmq.connect()
        logger.info("📡 Connected to RabbitMQ")

        # Create monitors
        self.posts_monitor = PostsMonitor(self.page, self.rabbitmq)

        # Create second page for notifications
        context = self.page.context
        notif_page = await context.new_page()
        self.notifications_monitor = NotificationsMonitor(notif_page, self.rabbitmq)

        # Register message handlers
        self.rabbitmq.register_handler("timeline_post", self.handle_post)
        self.rabbitmq.register_handler("notification", self.handle_notification)

        # Start monitors
        await self.posts_monitor.start_monitoring()
        await self.notifications_monitor.start_monitoring()

    async def handle_post(self, message: BotMessage):
        """Handle timeline post for potential reply"""
        try:
            data = message.data
            logger.info(f"Processing post from @{data.get('author')}")

            # Decide whether to reply (based on probability)
            import random
            if random.random() < self.config.reply_probability:
                reply = self.reply_generator.generate_reply(data)
                if reply:
                    logger.info(f"💬 Generated reply: {reply[:100]}...")
                    # Here you would post the reply using xbot
                    await self.post_reply(data.get('id'), reply)
            else:
                logger.debug("Skipped reply (probability check)")

        except Exception as e:
            logger.error(f"Error handling post: {e}")

    async def handle_notification(self, message: BotMessage):
        """Handle notification for potential response"""
        try:
            data = message.data
            notif_type = data.get('type')

            # Respond to mentions and replies
            if notif_type in ['mention', 'reply']:
                logger.info(f"📨 Responding to {notif_type} from @{data.get('from_handle')}")
                reply = self.reply_generator.generate_reply(data)
                if reply:
                    logger.info(f"💬 Generated response: {reply[:100]}...")
                    # Here you would post the response
                    await self.post_reply(None, reply, mention=data.get('from_handle'))

        except Exception as e:
            logger.error(f"Error handling notification: {e}")

    async def post_reply(self, post_id: Optional[str], text: str, mention: Optional[str] = None):
        """Post a reply to X/Twitter"""
        try:
            # Add mention if needed
            if mention and not text.startswith(f"@{mention}"):
                text = f"@{mention} {text}"

            # Navigate to compose
            await self.page.click('[data-testid="SideNav_NewTweet_Button"]')
            await asyncio.sleep(2)

            # Type reply
            compose_box = await self.page.wait_for_selector('[data-testid="tweetTextarea_0"]')
            await compose_box.type(text)
            await asyncio.sleep(1)

            # Post
            await self.page.click('[data-testid="tweetButtonInline"]')
            logger.info(f"✅ Posted reply: {text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to post reply: {e}")

    async def start(self):
        """Start the orchestrator"""
        self.running = True
        logger.info("🚀 Starting 4Bot Orchestrator...")

        # Setup components
        await self.setup_browser()
        self.reply_generator.start()
        await self.setup_monitors()

        # Start message consumption loop
        asyncio.create_task(self.consume_messages())

        logger.info("✅ 4Bot Orchestrator is running!")
        logger.info(f"   Profile: {self.config.profile_name}")
        logger.info(f"   User: {self.config.x_user}")
        logger.info(f"   Reply Rate: {self.config.reply_probability * 100}%")
        logger.info(f"   Max Replies/Hour: {self.config.max_replies_per_hour}")

    async def consume_messages(self):
        """Consume messages from RabbitMQ"""
        # Start consuming in a non-blocking thread
        import threading

        def consume_responses():
            try:
                self.rabbitmq.consume_responses()
            except Exception as e:
                logger.error(f"Error consuming responses: {e}")

        # Start consumer thread
        consumer_thread = threading.Thread(target=consume_responses, daemon=True)
        consumer_thread.start()
        logger.info("📨 Started message consumer thread")

    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        logger.info("🛑 Stopping 4Bot Orchestrator...")

        # Stop monitors
        if self.posts_monitor:
            await self.posts_monitor.stop_monitoring()
        if self.notifications_monitor:
            await self.notifications_monitor.stop_monitoring()

        # Close connections
        self.reply_generator.stop()
        self.rabbitmq.close()

        # Close browser
        if self.browser:
            await self.browser.close()

        logger.info("✅ 4Bot Orchestrator stopped")


async def main():
    """Main entry point"""
    # Create configuration
    config = BotConfig()

    # Create and start orchestrator
    orchestrator = FourBotOrchestrator(config)

    # Track shutdown event
    shutdown_event = asyncio.Event()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start orchestrator with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await orchestrator.start()
                break
            except Exception as e:
                logger.error(f"Start attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                else:
                    raise

        # Keep running until shutdown
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await orchestrator.stop()
        sys.exit(0)


if __name__ == "__main__":
    # Run the orchestrator
    asyncio.run(main())
