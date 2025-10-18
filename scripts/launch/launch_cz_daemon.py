#!/usr/bin/env python3
"""
CZ Auto-Responder Daemon Launcher
Launches a headless daemon that monitors X/Twitter and replies as CZ
"""

import asyncio
import json
import logging
import os
from typing import Any as _Moved
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional
import aiohttp

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.event_interceptor import EventInterceptor, PostEvent
from xbot.facade import XBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CZ-DAEMON] %(levelname)s: %(message)s'
)
logger = logging.getLogger('cz_daemon')


class VTermClient:
    """Simple HTTP client for VTerm server"""

    def __init__(self, base_url: str = "http://127.0.0.1:9876", token: Optional[str] = None):
        self.base_url = base_url
        self.headers = {"X-VTerm-Token": token} if token else {}

    async def run_command(self, cmd: str, timeout: int = 30) -> dict:
        """Run a command through VTerm HTTP"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/run",
                    json={"cmd": cmd, "timeout": timeout},
                    headers=self.headers
                ) as response:
                    return await response.json()
            except Exception as e:
                logger.error(f"VTerm command failed: {e}")
                return {"exit_code": 1, "lines": [], "error": str(e)}

    async def health_check(self) -> bool:
        """Check if VTerm server is running"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
            except:
                return False


class CZReplyEngine:
    """CZ persona reply generator using Claude via VTerm"""

    def __init__(self, vterm: VTermClient):
        self.vterm = vterm
        self.cz_prompt = self._load_cz_prompt()
        self.own_handles = {"4botbsc", "4bot", "4botbsc@gmail.com"}

    def _load_cz_prompt(self) -> str:
        """Load CZ persona prompt"""
        prompt_path = Path("CLAUDE.md")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def is_self_post(self, author: str) -> bool:
        """Check if post is from our own account"""
        author_lower = author.lower()
        return any(handle.lower() in author_lower for handle in self.own_handles)

    async def generate_reply(self, post: PostEvent) -> Optional[str]:
        """Generate CZ-style reply"""
        try:
            # Filter self-posts
            if self.is_self_post(post.author_handle):
                logger.debug(f"Skipping self-post from @{post.author_handle}")
                return None

            content_lower = post.content.lower()

            # Quick FUD response
            fud_terms = ['scam', 'rug', 'ponzi', 'dead', 'crash', 'fraud', 'fake']
            if any(term in content_lower for term in fud_terms):
                return "4"

            # Building encouragement
            build_terms = ['build', 'buidl', 'ship', 'launch', 'develop', 'create']
            if any(term in content_lower for term in build_terms):
                responses = [
                    "This is the way! Keep BUIDLing 🚀",
                    "Love to see it. We build through everything.",
                    "Exactly right. Focus on building, not the noise.",
                    "Building is the answer. Always has been.",
                ]
                import random
                return random.choice(responses)

            # Market/price discussions
            if 'price' in content_lower or 'chart' in content_lower or 'dump' in content_lower:
                return "Less focus on charts, more focus on BUIDLing. Long term wins."

            # Generate contextual reply
            prompt = f"""System: {self.cz_prompt[:1000]}

Context: Reply to this X post as CZ.
Author: @{post.author_handle}
Post: {post.content[:500]}

Instructions:
- Reply in CZ's voice (calm, building-focused, encouraging)
- Use "4" for FUD/negativity
- Keep under 280 characters
- Be authentic and concise
- Focus on building and long-term thinking

Reply (text only, no quotes or prefixes):"""

            cmd = f'echo {json.dumps(prompt)} | claude --dangerously-skip-permissions --max-tokens 100'
            result = await self.vterm.run_command(cmd, timeout=20)

            if result.get('exit_code') == 0:
                lines = result.get('lines', [])
                reply = '\n'.join(lines).strip()

                # Clean the reply
                reply = reply.strip('"\'`').replace('Reply:', '').strip()

                if reply and len(reply) <= 280:
                    return reply

            # Fallback responses
            fallbacks = [
                "Keep building! The future belongs to builders.",
                "Focus on what you can control. BUIDL.",
                "Long-term thinking wins. Always.",
                "This is the way. Keep pushing forward.",
            ]
            return random.choice(fallbacks)

        except Exception as e:
            logger.error(f"Reply generation error: {e}")
            return "Keep BUIDLing! 🚀"


class CZDaemon:
    """Main CZ auto-responder daemon"""

    def __init__(self):
        self.config = Config.from_env()
        self.config.headless = True
        self.vterm = VTermClient()
        self.reply_engine = CZReplyEngine(self.vterm)
        self.bot = XBot(self.config)
        self.running = False
        self.replied_posts = set()
        self.reply_count = 0
        self.last_reply_time = time.time()

    async def ensure_vterm_running(self):
        """Ensure VTerm HTTP server is running"""
        if await self.vterm.health_check():
            logger.info("✅ VTerm server is running")
            return True

        logger.info("Starting VTerm HTTP server...")
        # Start VTerm HTTP server as subprocess
        subprocess.Popen([
            sys.executable, "-m", "xbot.vterm_http",
            "--host", "127.0.0.1",
            "--port", "9876"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for server to start
        for _ in range(30):
            await asyncio.sleep(1)
            if await self.vterm.health_check():
                logger.info("✅ VTerm server started")
                return True

        logger.error("Failed to start VTerm server")
        return False

    async def should_reply(self, post: PostEvent) -> bool:
        """Determine if we should reply to this post"""
        # Skip if already replied
        if post.id in self.replied_posts:
            return False

        # Skip self-posts
        if self.reply_engine.is_self_post(post.author_handle):
            logger.debug(f"Filtered self-post from @{post.author_handle}")
            return False

        # Skip short posts
        if len(post.content) < 10:
            return False

        # Rate limiting (max 20 replies per hour)
        current_time = time.time()
        if current_time - self.last_reply_time < 3600:  # Within the hour
            if self.reply_count >= 20:
                logger.debug("Rate limit reached")
                return False
        else:
            # Reset hourly counter
            self.reply_count = 0
            self.last_reply_time = current_time

        # Higher chance for mentions
        if '@4bot' in post.content.lower() or post.is_reply:
            import random
            return random.random() < 0.9  # 90% for mentions

        # Lower chance for general timeline
        import random
        return random.random() < 0.3  # 30% for general posts

    async def handle_post(self, post: PostEvent):
        """Handle incoming post"""
        try:
            if not await self.should_reply(post):
                return

            logger.info(f"📝 Processing post from @{post.author_handle}: {post.content[:100]}...")

            # Generate reply
            reply = await self.reply_engine.generate_reply(post)

            if reply:
                # Post the reply
                status_url = f"{self.config.base_url}/i/web/status/{post.id}"
                await self.bot.reply(status_url, reply)

                # Track reply
                self.replied_posts.add(post.id)
                self.reply_count += 1

                logger.info(f"✅ Replied: {reply[:100]}...")

                # Small delay to avoid rate limiting
                await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Error handling post: {e}")

    async def run(self):
        """Run the daemon"""
        self.running = True
        logger.info("🚀 Starting CZ Auto-Responder Daemon")
        logger.info("   Mode: Headless In-Memory")
        logger.info("   Profile: 4botbsc")
        logger.info("   Self-filtering: ENABLED")

        # Ensure VTerm is running
        if not await self.ensure_vterm_running():
            logger.error("Cannot start without VTerm server")
            return

        # Setup browser
        from xbot.profiles import profile_paths
        storage, user_dir = profile_paths("4botbsc")
        self.config.storage_state = storage
        self.config.user_data_dir = user_dir

        async with Browser(self.config, label="cz_daemon") as browser:
            page = browser.page

            # Login if needed
            await login_if_needed(page, self.config)

            # Navigate to home
            await page.goto(self.config.base_url + "/home", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Setup event interceptor
            interceptor = EventInterceptor()
            interceptor.add_callback(self.handle_post)
            await interceptor.start_monitoring(page)

            # Create notifications page
            notif_page = await browser._ctx.new_page()
            await notif_page.goto(self.config.base_url + "/notifications", wait_until="domcontentloaded")

            # Setup notifications interceptor
            notif_interceptor = EventInterceptor()
            notif_interceptor.add_callback(self.handle_post)
            await notif_interceptor.start_monitoring(notif_page)

            logger.info("✅ Daemon is running and monitoring")
            logger.info("   Filtering own posts: YES")
            logger.info("   Rate limit: 20/hour")
            logger.info("   Reply chance: 30% general, 90% mentions")
            logger.info("\nPress Ctrl+C to stop")

            # Keep running
            while self.running:
                await asyncio.sleep(10)

                # Log stats periodically
                if self.reply_count > 0 and self.reply_count % 5 == 0:
                    logger.info(f"📊 Stats: {self.reply_count} replies, {len(self.replied_posts)} unique posts")

    async def stop(self):
        """Stop the daemon"""
        self.running = False
        logger.info("🛑 Stopping daemon...")


async def main():
    """Main entry point"""
    daemon = CZDaemon()

    # Setup signal handlers
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start daemon
        daemon_task = asyncio.create_task(daemon.run())

        # Wait for shutdown
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await daemon.stop()
        logger.info("✅ Daemon stopped cleanly")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║               CZ Auto-Responder Daemon v1.0                  ║
║                                                              ║
║  🤖 Monitoring X/Twitter posts and replying as CZ           ║
║  🔒 Self-post filtering enabled                             ║
║  ⚡ Headless in-memory execution                            ║
║  🎯 Smart contextual replies                                ║
╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
