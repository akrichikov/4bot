#!/usr/bin/env python3
"""
CZ VTerm RabbitMQ Daemon - Complete Notification Pipeline with Tab Management
Monitors @4botbsc mentions → VTerm HTTP Queue → RabbitMQ → Reply Posting
"""

import asyncio
import json
import logging
from typing import Any as _Moved
import os
import sys
import time
import uuid
import aiohttp
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import pika
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlparse

try:
    import xbot  # noqa: F401
except Exception:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.cookies import load_cookie_json, merge_into_storage
from xbot.profiles import storage_state_path
from playwright.async_api import Page, BrowserContext, async_playwright
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-VTERM-DAEMON] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_vterm_daemon')


@dataclass
class NotificationEvent:
    """Parsed notification event for @4botbsc mentions"""
    id: str
    type: str  # mention, reply
    author: str
    author_handle: str
    content: str
    url: str
    timestamp: str

    def to_vterm_request(self) -> Dict[str, Any]:
        """Convert to VTerm request format"""
        return {
            "notification_id": self.id,
            "type": self.type,
            "author": self.author_handle,
            "content": self.content,
            "reply_url": self.url,
            "timestamp": self.timestamp
        }


class TabManager:
    """Manages browser tabs/contexts for isolated operations"""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.auth_state = None
        self.cookies = []

    async def initialize(self):
        """Initialize playwright browser"""
        self.playwright = await async_playwright().start()

        # Load authentication
        cookie_path = Path("auth_data/x_cookies.json")
        if cookie_path.exists():
            self.cookies = load_cookie_json(cookie_path)
            logger.info(f"✅ Loaded {len(self.cookies)} cookies for tab management")

        # Load storage state if exists
        storage_path = storage_state_path("4botbsc")
        auth_mode = (os.getenv('AUTH_MODE') or '').lower()
        if auth_mode == 'cookies':
            self.auth_state = None
            logger.info("🔐 AUTH_MODE=cookies → using in-memory cookies only")
        elif storage_path.exists():
            with open(storage_path) as f:
                self.auth_state = json.load(f)

        # Choose engine (default webkit for Safari-like behaviour)
        engine = (os.getenv('BROWSER_NAME') or os.getenv('BROWSER') or 'webkit').lower()
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]
        if engine == 'webkit':
            self.browser = await self.playwright.webkit.launch(headless=True)
        elif engine == 'firefox':
            self.browser = await self.playwright.firefox.launch(headless=True)
        else:
            self.browser = await self.playwright.chromium.launch(headless=True, args=launch_args)

    @asynccontextmanager
    async def get_authenticated_tab(self, label: str = "tab"):
        """Get an authenticated browser tab that auto-closes"""
        context = None
        page = None

        try:
            # Create new context with auth
            ua = os.getenv('USER_AGENT') or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
            context = await self.browser.new_context(
                storage_state=self.auth_state,
                viewport={"width": 1920, "height": 1080},
                user_agent=ua
            )

            # Add cookies; if storage_state exists they'll override where applicable
            if self.cookies:
                try:
                    await context.add_cookies(self.cookies)
                except Exception:
                    pass

            # Create new page
            page = await context.new_page()
            logger.info(f"📑 Created authenticated tab: {label}")

            yield page

        finally:
            # Cleanup
            if page:
                await page.close()
                logger.info(f"🗑️ Closed tab: {label}")
            if context:
                await context.close()

    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class VTermHTTPClient:
    """Client for VTerm HTTP queue endpoints"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None):
        self.base_url = f"http://{host}:{port}"
        self.token = token
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-VTerm-Token"] = self.token
        return headers

    async def queue_cz_reply_job(self, notification: NotificationEvent) -> Optional[str]:
        """Queue a CZ reply generation job in VTerm"""
        try:
            # Create Python script for CZ reply generation
            script = f"""
import json
import random

# Load CZ persona
notification = {json.dumps(notification.to_vterm_request())}

def generate_cz_reply(notif):
    content = notif.get('content', '').lower()
    author = notif.get('author', 'user')

    # FUD detection
    if any(word in content for word in ['scam', 'rug', 'crash', 'dead']):
        return "4"

    # Building content
    if any(word in content for word in ['build', 'develop', 'launch']):
        replies = [
            "This is the way! Keep BUIDLing 🚀",
            "Love to see builders building through everything.",
            "Exactly right. We build through all market conditions."
        ]
        return random.choice(replies)

    # Questions
    if '?' in notif.get('content', ''):
        if 'when' in content:
            return "The best time was yesterday, the next best time is today. Focus on building."
        elif 'how' in content:
            return "Start small, learn constantly, build consistently. The path reveals itself."
        else:
            return "Great question! The answer is always: keep building. BUIDL is the way."

    # Mentions - encouraging responses
    replies = [
        "Appreciate you! Let's keep building the future together 🚀",
        "This is the mindset. Long-term thinking always wins.",
        "100% agreed. The future is decentralized and we're building it.",
        "Stay focused on what matters: building value for users.",
        "Keep pushing forward. Every day we're creating the future."
    ]
    return random.choice(replies)

# Generate reply
reply = generate_cz_reply(notification)

# Output in structured format
result = {{
    "notification_id": notification['notification_id'],
    "reply_url": notification['reply_url'],
    "reply_text": reply,
    "author": notification['author']
}}

print(json.dumps(result))
"""
            # Submit job to VTerm queue: run a here-doc Python script to emit a single JSON line
            cmd = f"python3 - <<'PY'\n{script}\nPY"
            payload = {"cmd": cmd, "timeout": 30.0}

            async with self.session.post(
                f"{self.base_url}/queue/run",
                json=payload,
                headers=self._headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    job_id = (result.get('job_id') or result.get('id'))
                    logger.info(f"📤 Queued VTerm job {job_id} for @{notification.author_handle}")
                    return job_id
                else:
                    logger.error(f"Failed to queue job: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error queuing VTerm job: {e}")
            return None

    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a VTerm job"""
        try:
            async with self.session.get(f"{self.base_url}/queue/{job_id}", headers=self._headers()) as response:
                if response.status != 200:
                    return None
                job = await response.json()
                status = job.get('status')
                if status not in ('done', 'completed'):
                    return None
                # vterm_http stores structured VTermResult JSON under 'result'
                res = job.get('result') or {}
                # Prefer JSON objects parsed from the output
                objs = res.get('json_objects') or []
                if objs:
                    return objs[0]
                raw = (res.get('raw_text') or '').strip()
                if raw:
                    try:
                        return json.loads(raw)
                    except Exception:
                        pass
                return None
        except Exception as e:
            logger.error(f"Error getting job result: {e}")
            return None


class NotificationMonitor:
    """Monitors X/Twitter notifications for @4botbsc mentions"""

    def __init__(self):
        self.processed_ids = set()
        self.tab_manager = TabManager()

    async def initialize(self):
        """Initialize tab manager"""
        await self.tab_manager.initialize()

    async def get_4botbsc_mentions(self) -> List[NotificationEvent]:
        """Get new @4botbsc mentions from notifications"""
        mentions = []

        async with self.tab_manager.get_authenticated_tab("notification_monitor") as page:
            try:
                # Navigate to mentions
                await page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded")
                await asyncio.sleep(3)

                # Extract notifications
                script = r"""
                () => {
                    const notifications = [];
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');

                    articles.forEach(article => {
                        try {
                            // Get text content
                            const textEl = article.querySelector('[data-testid="tweetText"]');
                            const text = textEl ? textEl.textContent : '';

                            // Check for @4botbsc mention
                            if (!text.toLowerCase().includes('@4botbsc')) return;

                            // Get author
                            const links = article.querySelectorAll('a[href^="/"]');
                            let author = '';
                            let authorHandle = '';
                            for (const link of links) {
                                const href = link.getAttribute('href');
                                if (href && href.match(/^\/[^\/]+$/) && !href.includes('status')) {
                                    authorHandle = href.substring(1);
                                    const nameEl = link.querySelector('[dir="ltr"] > span');
                                    author = nameEl ? nameEl.textContent : authorHandle;
                                    break;
                                }
                            }

                            // Skip our own posts
                            if (authorHandle.toLowerCase() === '4botbsc') return;

                            // Get URL
                            const statusLink = article.querySelector('a[href*="/status/"]');
                            const url = statusLink ? statusLink.href : '';
                            const id = url ? url.split('/status/')[1]?.split('/')[0] : '';

                            if (id && text && authorHandle) {
                                notifications.push({
                                    id: id,
                                    type: 'mention',
                                    author: author,
                                    author_handle: authorHandle,
                                    content: text,
                                    url: url,
                                    timestamp: new Date().toISOString()
                                });
                            }
                        } catch (e) {}
                    });

                    return notifications;
                }
                """

                notifications_data = await page.evaluate(script)

                # Also use enhanced extractor via console to improve coverage
                collected: list[dict] = []
                def _on_console(msg):
                    try:
                        t = msg.text
                        if t.startswith('__ENHANCED_NOTIFICATION__:'):
                            data = json.loads(t.split(':', 1)[1])
                            collected.append(data)
                    except Exception:
                        pass
                page.on("console", _on_console)
                try:
                    script_path = (Path(__file__).resolve().parents[2] / "scripts/notification/enhanced_notification_extractor.js")
                    if script_path.exists():
                        await page.evaluate(script_path.read_text(encoding='utf-8'))
                        await asyncio.sleep(1)
                        for d in collected:
                            url = d.get('url') or ''
                            if '/status/' not in url:
                                continue
                            nid = url.split('/status/')[1].split('/')[0]
                            author_handle = d.get('from_handle') or ''
                            author = d.get('from_name') or author_handle
                            content = d.get('content') or d.get('full_text') or ''
                            row = {
                                'id': nid,
                                'type': d.get('type') or 'mention',
                                'author': author,
                                'author_handle': author_handle,
                                'content': content,
                                'url': url,
                                'timestamp': d.get('timestamp') or datetime.now().isoformat(),
                            }
                            notifications_data.append(row)
                except Exception:
                    pass

                # Filter new mentions (only those that reference @4botbsc and are not self)
                for data in notifications_data:
                    try:
                        cid = data.get('id')
                        if not cid or cid in self.processed_ids:
                            continue
                        content = (data.get('content') or '').lower()
                        author_handle = (data.get('author_handle') or '').lower()
                        url = data.get('url') or ''
                        if ('@4botbsc' not in content) or ('/status/' not in url) or (author_handle == '4botbsc'):
                            continue
                        event = NotificationEvent(
                            id=cid,
                            type=data.get('type') or 'mention',
                            author=data.get('author') or data.get('author_handle') or '',
                            author_handle=data.get('author_handle') or '',
                            content=data.get('content') or '',
                            url=url,
                            timestamp=data.get('timestamp') or datetime.now().isoformat(),
                        )
                        self.processed_ids.add(cid)
                        mentions.append(event)
                        logger.info(f"📥 New @4botbsc mention from @{event.author_handle}")
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Error getting mentions: {e}")

        return mentions

    async def cleanup(self):
        """Cleanup resources"""
        await self.tab_manager.cleanup()


class RabbitMQBridge:
    """Bridges VTerm results to RabbitMQ and handles reply posting"""

    def __init__(self):
        self.manager = RabbitMQManager()
        self.manager.connect()
        self.tab_manager = TabManager()

    async def initialize(self):
        """Initialize tab manager"""
        await self.tab_manager.initialize()

    def publish_reply_to_rabbitmq(self, reply_data: Dict[str, Any]) -> bool:
        """Publish reply to RabbitMQ for processing"""
        try:
            message = BotMessage(
                message_id=f"reply_{reply_data.get('notification_id')}_{datetime.now().timestamp()}",
                message_type="cz_reply",
                timestamp=datetime.now().isoformat(),
                source="vterm",
                data=reply_data,
                metadata={"persona": "CZ", "processed_by": "vterm"}
            )

            success = self.manager.publish_message(
                message=message,
                routing_key='4bot.request.reply'
            )

            if success:
                logger.info(f"📨 Published to RabbitMQ: reply for @{reply_data.get('author')}")

            return success

        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")
            return False

    async def post_reply_to_twitter(self, reply_data: Dict[str, Any]) -> bool:
        """Post reply to Twitter using authenticated tab"""
        async with self.tab_manager.get_authenticated_tab(f"reply_{reply_data.get('notification_id')}") as page:
            try:
                url = reply_data.get('reply_url')
                text = reply_data.get('reply_text')

                if not url or not text:
                    return False

                # Ensure session is authenticated; attempt cookie-based first, then credential login if needed
                try:
                    cfg = Config.from_env()
                    cfg.headless = True
                    cfg.persist_session = False
                    # Force WebKit/Safari-like engine semantics
                    cfg.browser_name = 'webkit'  # type: ignore[assignment]
                    await login_if_needed(page, cfg)
                except Exception:
                    pass

                # Navigate to tweet
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                # Click reply button
                reply_btn = await page.query_selector('[data-testid="reply"]')
                if reply_btn:
                    await reply_btn.click()
                    await asyncio.sleep(2)

                    # Type reply
                    reply_box = await page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
                    await reply_box.click()
                    await page.keyboard.type(text, delay=50)
                    await asyncio.sleep(1)

                    # Send
                    send_btn = await page.query_selector('[data-testid="tweetButton"]')
                    if send_btn:
                        is_disabled = await send_btn.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            await send_btn.click()
                            await asyncio.sleep(3)
                            logger.info(f"✅ Posted reply to @{reply_data.get('author')}: {text[:50]}...")
                            return True

                    # Try keyboard shortcut
                    await page.keyboard.press('Control+Enter')
                    await asyncio.sleep(3)
                    logger.info(f"✅ Posted reply (keyboard) to @{reply_data.get('author')}")
                    return True

                return False

            except Exception as e:
                logger.error(f"Failed to post reply: {e}")
                return False

    def start_reply_consumer(self):
        """Start consuming replies from RabbitMQ"""
        def handle_reply(message: BotMessage):
            """Handle incoming reply from RabbitMQ"""
            try:
                # Run async posting
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.post_reply_to_twitter(message.data)
                )
                loop.close()

                # Publish result
                response = BotMessage(
                    message_id=f"response_{message.message_id}",
                    message_type="reply_posted",
                    timestamp=datetime.now().isoformat(),
                    source="reply_poster",
                    data={
                        "original_id": message.message_id,
                        "success": success,
                        "posted_at": datetime.now().isoformat() if success else None
                    }
                )

                self.manager.publish_message(
                    message=response,
                    routing_key='4bot.response.reply'
                )

            except Exception as e:
                logger.error(f"Error handling reply: {e}")

        self.manager.register_handler("cz_reply", handle_reply)
        logger.info("🎧 Starting RabbitMQ reply consumer...")
        self.manager.consume_requests()

    async def cleanup(self):
        """Cleanup resources"""
        await self.tab_manager.cleanup()
        self.manager.close()


class CZVTermDaemon:
    """Main daemon orchestrating the notification pipeline"""

    def __init__(self):
        self.notification_monitor = NotificationMonitor()
        self.vterm_client = None
        self.rabbitmq_bridge = RabbitMQBridge()
        self.consumer_thread = None
        self.running = True

    async def initialize(self):
        """Initialize all components"""
        await self.notification_monitor.initialize()
        await self.rabbitmq_bridge.initialize()

        # Initialize VTerm client
        self.vterm_client = VTermHTTPClient(
            host="127.0.0.1",
            port=8765,
            token=os.getenv("VTERM_TOKEN")
        )

        # Start RabbitMQ consumer in thread
        self.consumer_thread = threading.Thread(
            target=self.rabbitmq_bridge.start_reply_consumer,
            daemon=True
        )
        self.consumer_thread.start()
        logger.info("✅ All components initialized")

    async def process_notification(self, notification: NotificationEvent):
        """Process a single notification through the pipeline"""
        try:
            # 1. Send to VTerm for reply generation
            job_id = await self.vterm_client.queue_cz_reply_job(notification)

            if not job_id:
                logger.error(f"Failed to queue job for {notification.id}")
                return

            # 2. Wait for VTerm result (with timeout)
            max_attempts = 30  # 30 seconds timeout
            for _ in range(max_attempts):
                result = await self.vterm_client.get_job_result(job_id)
                if result:
                    # 3. Publish to RabbitMQ
                    self.rabbitmq_bridge.publish_reply_to_rabbitmq(result)
                    logger.info(f"✅ Processed notification {notification.id} through pipeline")
                    break
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error processing notification: {e}")

    async def monitor_loop(self):
        """Main monitoring loop"""
        async with self.vterm_client:
            while self.running:
                try:
                    # Get new mentions
                    mentions = await self.notification_monitor.get_4botbsc_mentions()

                    # Process each mention
                    for mention in mentions:
                        await self.process_notification(mention)

                    # Wait before next check
                    await asyncio.sleep(30)

                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")
                    await asyncio.sleep(10)

    async def run(self):
        """Run the daemon"""
        logger.info("🚀 Starting CZ VTerm RabbitMQ Daemon")
        logger.info("   Pipeline: Notifications → VTerm Queue → RabbitMQ → Twitter")
        logger.info("   Filter: @4botbsc mentions only ✅")
        logger.info("   Tab Management: Auto-cleanup enabled ✅")
        logger.info("   RabbitMQ: Persistent queues confirmed ✅")

        await self.initialize()
        await self.monitor_loop()

    async def cleanup(self):
        """Cleanup all resources"""
        self.running = False
        await self.notification_monitor.cleanup()
        await self.rabbitmq_bridge.cleanup()
        logger.info("🛑 Daemon stopped cleanly")


async def main():
    """Main entry point"""
    daemon = CZVTermDaemon()

    try:
        await daemon.run()
    except KeyboardInterrupt:
        logger.info("⛔ Daemon stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await daemon.cleanup()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         CZ VTERM RABBITMQ DAEMON - ACTIVATED                 ║
║                                                               ║
║  📋 Pipeline:                                                ║
║     1. Monitor @4botbsc mentions                             ║
║     2. Queue in VTerm HTTP for CZ reply generation          ║
║     3. Publish to RabbitMQ (persistent queues)              ║
║     4. Post replies with tab management                      ║
║                                                               ║
║  ✅ Headless Mode                                           ║
║  ✅ Tab Auto-cleanup                                        ║
║  ✅ Durable RabbitMQ Queues                                 ║
║  ✅ Authenticated Sessions                                   ║
║                                                               ║
║           Press Ctrl+C to stop                               ║
╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
