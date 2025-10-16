#!/usr/bin/env python3
"""
CZ Reply Poster - Autonomous Reply Publishing
Consumes generated CZ replies from RabbitMQ and posts them to Twitter/X
"""

import asyncio
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, Page
from rabbitmq_manager import RabbitMQManager, BotMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('CZ-REPLY-POSTER')


class ReplyPoster:
    """Posts CZ-generated replies to Twitter/X"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.rabbitmq = RabbitMQManager()
        self.storage_state = Path("config/profiles/4botbsc/storageState.json")
        self.replies_posted = 0
        self.replies_failed = 0
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def setup_browser(self):
        """Initialize authenticated browser session"""
        logger.info("🌐 Setting up browser for reply posting...")

        if not self.storage_state.exists():
            logger.error(f"❌ Authentication file not found: {self.storage_state}")
            return False

        playwright = await async_playwright().start()

        # Use Safari/WebKit for better Twitter/X compatibility
        self.browser = await playwright.webkit.launch(
            headless=True
        )

        self.context = await self.browser.new_context(
            storage_state=str(self.storage_state),
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = await self.context.new_page()
        logger.info("✅ Browser ready for posting replies")
        return True

    async def post_reply(self, tweet_url: str, reply_text: str):
        """Post a reply to a specific tweet"""
        import traceback
        try:
            logger.info(f"🎯 Navigating to tweet: {tweet_url}")
            await self.page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            logger.info("✓ Page loaded")

            # Click reply button
            logger.info("🔍 Looking for reply button...")
            reply_button = await self.page.query_selector('[data-testid="reply"]')
            if not reply_button:
                logger.error("❌ Could not find reply button")
                return False
            logger.info("✓ Found reply button")

            await reply_button.click()
            await self.page.wait_for_timeout(1000)
            logger.info("✓ Clicked reply button")

            # Type the reply
            logger.info("🔍 Looking for reply text box...")
            reply_box = await self.page.query_selector('[data-testid="tweetTextarea_0"]')
            if not reply_box:
                logger.error("❌ Could not find reply text box")
                return False
            logger.info("✓ Found reply text box")

            await reply_box.fill(reply_text)
            await self.page.wait_for_timeout(1000)
            logger.info(f"✓ Typed reply: {reply_text}")

            # Click send button
            logger.info("🔍 Looking for send button...")
            send_button = await self.page.query_selector('[data-testid="tweetButton"]')
            if not send_button:
                logger.error("❌ Could not find send button")
                return False
            logger.info("✓ Found send button")

            await send_button.click()
            await self.page.wait_for_timeout(3000)  # Wait for post to complete
            logger.info("✓ Clicked send button")

            logger.info(f"✅ Reply posted successfully!")
            logger.info(f"   Reply text: {reply_text}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to post reply: {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def handle_cz_reply_generated(self, message: BotMessage):
        """Handle CZ reply generation completion - post the reply"""
        logger.info("📥 Received generated CZ reply")

        data = message.data
        post_url = data.get('post_url', '')
        author = data.get('author_handle', 'unknown')
        reply_text = data.get('reply_text', '')

        logger.info(f"   From VTerm: Reply to @{author}")
        logger.info(f"   Reply: {reply_text}")
        logger.info(f"   Target: {post_url}")

        if not post_url or not reply_text:
            logger.error("❌ Missing required data in message")
            self.replies_failed += 1
            return

        # Post the reply using thread pool to avoid event loop conflicts
        def run_async_post():
            """Helper to run async post_reply in a new thread"""
            import traceback
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(self.post_reply(post_url, reply_text))
                    return success
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Exception in async post: {e}")
                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                return False

        try:
            # Submit to thread pool and wait for result
            future = self.executor.submit(run_async_post)
            success = future.result(timeout=60)  # 60 second timeout

            if success:
                self.replies_posted += 1
                logger.info(f"📊 Stats: {self.replies_posted} posted, {self.replies_failed} failed")
            else:
                self.replies_failed += 1
                logger.error(f"📊 Stats: {self.replies_posted} posted, {self.replies_failed} failed")

        except Exception as e:
            logger.error(f"❌ Exception posting reply: {e}")
            self.replies_failed += 1

    async def run(self):
        """Start the reply poster"""
        try:
            if not await self.setup_browser():
                logger.error("❌ Failed to setup browser")
                return

            # Connect to RabbitMQ
            if not self.rabbitmq.connect():
                logger.error("❌ Failed to connect to RabbitMQ")
                return

            # Register handler for generated replies
            self.rabbitmq.register_handler("cz_reply_generated", self.handle_cz_reply_generated)

            logger.info("👂 Listening for generated CZ replies on RabbitMQ...")
            logger.info("   Queue: 4bot_response")
            logger.info("   Message type: cz_reply_generated")
            logger.info("")

            # Start consuming - this blocks
            self.rabbitmq.consume_responses()

        except KeyboardInterrupt:
            logger.info("\n⏹️  Keyboard interrupt received")
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
    print("║           CZ Reply Poster - Autonomous Mode                  ║")
    print("║                                                              ║")
    print("║  Consuming generated replies and posting to Twitter/X        ║")
    print("║                                                              ║")
    print("║  Press Ctrl+C to stop                                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    poster = ReplyPoster()
    await poster.run()


if __name__ == "__main__":
    asyncio.run(main())
