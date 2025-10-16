#!/usr/bin/env python3
"""
CZ Auto-Responder Daemon
Headless daemon that monitors X/Twitter posts and replies contextually as CZ
Filters out self-posts and maintains rate limits
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Set, List
import aiohttp
import signal

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import login_if_needed
from xbot.event_interceptor import EventInterceptor, PostEvent
from xbot.facade import XBot
from xbot.vterm_http import VTermHTTPClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cz_auto_daemon')


@dataclass
class DaemonConfig:
    """Configuration for CZ Auto Daemon"""
    profile: str = "4botbsc"
    username: str = "4botbsc"
    headless: bool = True
    vterm_base: str = "http://127.0.0.1:9876"
    vterm_token: Optional[str] = None
    cz_prompt_path: str = "/Users/doctordre/projects/4bot/CLAUDE.md"

    # Rate limiting
    max_replies_per_hour: int = 15
    reply_probability: float = 0.4  # 40% chance to reply to general posts
    mention_reply_probability: float = 0.9  # 90% chance to reply to mentions

    # Content filtering
    min_post_length: int = 10  # Minimum characters to consider replying
    max_reply_length: int = 280  # Twitter character limit

    # Self-filtering
    own_handles: Set[str] = field(default_factory=lambda: {"4botbsc", "4bot"})


@dataclass
class ReplyStats:
    """Track reply statistics for rate limiting"""
    replies_this_hour: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    replied_to_posts: Set[str] = field(default_factory=set)

    def should_reset(self) -> bool:
        """Check if hourly counter should reset"""
        return datetime.now() - self.last_reset > timedelta(hours=1)

    def can_reply(self, max_per_hour: int) -> bool:
        """Check if we can reply based on rate limits"""
        if self.should_reset():
            self.replies_this_hour = 0
            self.last_reset = datetime.now()
        return self.replies_this_hour < max_per_hour

    def record_reply(self, post_id: str):
        """Record that we replied to a post"""
        self.replies_this_hour += 1
        self.replied_to_posts.add(post_id)


class CZPersonaGenerator:
    """Generate CZ-style replies using VTerm HTTP"""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.vterm = VTermHTTPClient(config.vterm_base, config.vterm_token)
        self.cz_prompt = self._load_cz_prompt()

    def _load_cz_prompt(self) -> str:
        """Load CZ persona from CLAUDE.md"""
        with open(self.config.cz_prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    async def generate_reply(self, post: PostEvent) -> Optional[str]:
        """Generate a CZ-style reply to a post"""
        try:
            # Analyze post content
            content_lower = post.content.lower()

            # Quick responses for specific patterns
            if self._is_fud(content_lower):
                return random.choice(["4", "4 🤷‍♂️", "4. Back to BUIDLing."])

            if self._is_building_related(content_lower):
                building_responses = [
                    "This is the way! Keep BUIDLing 🚀",
                    "Love to see it! We BUIDL through everything.",
                    "Exactly right. Focus on building, not the noise.",
                    "Building is the only constant. LFG! 🔨",
                    "This mindset wins. Keep pushing forward.",
                ]
                return random.choice(building_responses)

            # Generate contextual reply using LLM
            prompt = self._build_prompt(post)

            # Use VTerm to call Claude CLI for reply generation
            cmd = f"""printf %s {json.dumps(prompt)} | claude --dangerously-skip-permissions --max-tokens 100 --message "Generate a short X/Twitter reply (max 280 chars) as CZ based on this context. Reply only, no explanation:" """

            result = await self.vterm.run_command(cmd, timeout=15)

            if result and result.get('exit_code') == 0:
                reply = '\n'.join(result.get('lines', [])).strip()

                # Clean and validate reply
                reply = self._clean_reply(reply)

                if reply and len(reply) <= self.config.max_reply_length:
                    return reply

            # Fallback to pre-defined responses
            return self._get_fallback_reply(post)

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return self._get_fallback_reply(post)

    def _is_fud(self, text: str) -> bool:
        """Check if post contains FUD"""
        fud_words = [
            'scam', 'rug', 'dead', 'crash', 'ponzi', 'fraud',
            'fake', 'exit scam', 'dump', 'worthless', 'bubble'
        ]
        return any(word in text for word in fud_words)

    def _is_building_related(self, text: str) -> bool:
        """Check if post is about building"""
        build_words = [
            'build', 'buidl', 'develop', 'create', 'launch',
            'ship', 'deploy', 'release', 'code', 'program'
        ]
        return any(word in text for word in build_words)

    def _build_prompt(self, post: PostEvent) -> str:
        """Build prompt for LLM"""
        return f"""You are CZ. Core beliefs:
- Stay calm and BUIDL
- Long-term thinking wins
- Do the right thing
- Think abundance
- Own your results

Post from @{post.author_handle}: "{post.content[:500]}"

Reply style:
- Use "4" for FUD/negativity
- Encourage building
- Be concise and authentic
- Max 280 characters

Generate reply:"""

    def _clean_reply(self, reply: str) -> str:
        """Clean and validate reply"""
        # Remove any markdown or quotes
        reply = reply.strip('`"\'')

        # Remove "Reply:" or similar prefixes
        prefixes_to_remove = ['Reply:', 'Response:', 'CZ:', '@']
        for prefix in prefixes_to_remove:
            if reply.startswith(prefix):
                reply = reply[len(prefix):].strip()

        # Ensure it's not too long
        if len(reply) > self.config.max_reply_length:
            reply = reply[:self.config.max_reply_length-3] + "..."

        return reply

    def _get_fallback_reply(self, post: PostEvent) -> str:
        """Get a fallback reply when generation fails"""
        if post.is_reply or '@4bot' in post.content.lower():
            return random.choice([
                "Keep building! Every day we create the future 🚀",
                "This is the way. BUIDL through everything.",
                "Long-term thinking always wins. Stay focused.",
                "Appreciate you! Let's keep pushing forward.",
            ])

        return random.choice([
            "BUIDL 🔨",
            "Focus on what you can build, not what you can't control.",
            "The future is bright for builders.",
            "Keep shipping. Keep learning. Keep growing.",
        ])


class CZAutoDaemon:
    """Main daemon orchestrator"""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.stats = ReplyStats()
        self.generator = CZPersonaGenerator(config)
        self.xbot_config = Config.from_env()
        self.xbot_config.headless = config.headless
        self.bot = XBot(self.xbot_config)
        self.running = False
        self.browser = None

    async def start(self):
        """Start the daemon"""
        self.running = True
        logger.info(f"🚀 Starting CZ Auto Daemon")
        logger.info(f"   Profile: {self.config.profile}")
        logger.info(f"   Username: @{self.config.username}")
        logger.info(f"   Reply Rate: {self.config.max_replies_per_hour}/hour")
        logger.info(f"   General Reply Chance: {self.config.reply_probability*100}%")

        # Set up profile paths
        from xbot.profiles import profile_paths
        storage, user_dir = profile_paths(self.config.profile)
        self.xbot_config.storage_state = storage
        self.xbot_config.user_data_dir = user_dir

        # Start browser and login
        async with Browser(self.xbot_config, label="cz_daemon") as browser:
            self.browser = browser
            page = browser.page

            # Login if needed
            await login_if_needed(page, self.xbot_config)

            # Navigate to home timeline
            await page.goto(self.xbot_config.base_url + "/home", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Set up event interceptor for home timeline
            home_interceptor = EventInterceptor()
            home_interceptor.add_callback(self._handle_post)
            await home_interceptor.start_monitoring(page)

            # Create second page for notifications
            notif_page = await browser._ctx.new_page()
            await notif_page.goto(self.xbot_config.base_url + "/notifications", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Set up event interceptor for notifications
            notif_interceptor = EventInterceptor()
            notif_interceptor.add_callback(self._handle_post)
            await notif_interceptor.start_monitoring(notif_page)

            logger.info("✅ Daemon is running and monitoring posts")

            # Keep running
            while self.running:
                await asyncio.sleep(5)

                # Log stats periodically
                if random.random() < 0.1:  # 10% chance each cycle
                    logger.info(f"📊 Stats: {self.stats.replies_this_hour} replies this hour, "
                              f"{len(self.stats.replied_to_posts)} total posts replied to")

    async def _handle_post(self, post: PostEvent):
        """Handle an incoming post event"""
        try:
            # Skip if we've already replied to this post
            if post.id in self.stats.replied_to_posts:
                return

            # Filter out our own posts
            if self._is_own_post(post):
                logger.debug(f"Skipping own post from @{post.author_handle}")
                return

            # Check if post is too short
            if len(post.content) < self.config.min_post_length:
                return

            # Check rate limits
            if not self.stats.can_reply(self.config.max_replies_per_hour):
                logger.warning("Rate limit reached, skipping reply")
                return

            # Determine reply probability
            is_mention = '@4bot' in post.content.lower() or post.is_reply
            reply_prob = self.config.mention_reply_probability if is_mention else self.config.reply_probability

            # Decide whether to reply
            if random.random() > reply_prob:
                logger.debug(f"Skipping post from @{post.author_handle} (probability check)")
                return

            # Generate reply
            logger.info(f"🤔 Considering reply to @{post.author_handle}: {post.content[:100]}...")
            reply = await self.generator.generate_reply(post)

            if reply:
                # Post the reply
                await self._post_reply(post, reply)

                # Record stats
                self.stats.record_reply(post.id)

                logger.info(f"✅ Replied to @{post.author_handle}: {reply[:100]}...")

        except Exception as e:
            logger.error(f"Error handling post: {e}", exc_info=True)

    def _is_own_post(self, post: PostEvent) -> bool:
        """Check if this is our own post"""
        author_lower = post.author_handle.lower()
        return any(handle.lower() in author_lower for handle in self.config.own_handles)

    async def _post_reply(self, post: PostEvent, reply_text: str):
        """Post a reply to a tweet"""
        try:
            # Build the status URL
            status_url = f"{self.xbot_config.base_url.rstrip('/')}/i/web/status/{post.id}"

            # Use XBot to post reply
            await self.bot.reply(status_url, reply_text)

            # Add small delay to avoid rate limiting
            await asyncio.sleep(random.uniform(2, 5))

        except Exception as e:
            logger.error(f"Failed to post reply: {e}")

    async def stop(self):
        """Stop the daemon"""
        self.running = False
        logger.info("🛑 Stopping CZ Auto Daemon...")

        if self.browser:
            await self.browser.close()

        logger.info("✅ Daemon stopped")


async def main():
    """Main entry point"""
    # Load configuration
    config = DaemonConfig()

    # Override from environment if available
    if os.getenv('CZ_MAX_REPLIES'):
        config.max_replies_per_hour = int(os.getenv('CZ_MAX_REPLIES'))
    if os.getenv('CZ_REPLY_PROB'):
        config.reply_probability = float(os.getenv('CZ_REPLY_PROB'))

    # Create daemon
    daemon = CZAutoDaemon(config)

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("Received shutdown signal...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start daemon
        daemon_task = asyncio.create_task(daemon.start())

        # Wait for shutdown
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())