#!/usr/bin/env python3
"""
CZ Reply Poster - Autonomous Reply Publishing
Consumes generated CZ replies from RabbitMQ and posts them to Twitter/X
"""

import asyncio
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, Page
from xbot.rabbitmq_manager import RabbitMQManager, BotMessage
from xbot.cookies import load_cookies_best_effort
from xbot.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('CZ-REPLY-POSTER')


class ReplyPoster:
    """Posts CZ-generated replies to Twitter/X using ephemeral contexts"""

    def __init__(self):
        self.browser = None
        self.playwright = None
        self.rabbitmq = RabbitMQManager()
        self.storage_state = Path("config/profiles/4botbsc/storageState.json")
        self.replies_posted = 0
        self.replies_failed = 0
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def setup_browser(self):
        """Initialize browser (one persistent browser, ephemeral contexts per reply)"""
        logger.info("🌐 Setting up browser for reply posting (ephemeral contexts)...")

        self.playwright = await async_playwright().start()

        # Choose engine (default Safari/WebKit for this flow)
        engine = (os.getenv('BROWSER_NAME') or os.getenv('BROWSER') or 'webkit').lower()
        if engine == 'webkit':
            self.browser = await self.playwright.webkit.launch(headless=True)
        elif engine == 'firefox':
            self.browser = await self.playwright.firefox.launch(headless=True)
        else:
            self.browser = await self.playwright.chromium.launch(headless=True)

        logger.info("✅ Browser ready for posting replies (ephemeral mode)")
        return True

    async def create_ephemeral_context(self):
        """Create a fresh ephemeral browser context with authentication"""
        # Determine auth mode
        auth_mode = (os.getenv('AUTH_MODE') or '').lower()
        storage_state = None if auth_mode == 'cookies' else (str(self.storage_state) if self.storage_state.exists() else None)

        context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
        )

        # If cookie mode, add cookies using centralized helper
        if auth_mode == 'cookies':
            cfg = Config.from_env()
            cookies = load_cookies_best_effort(profile=cfg.profile_name)
            if cookies:
                await context.add_cookies(cookies)

        return context

    async def post_reply(self, tweet_url: str, reply_text: str):
        """Post a reply using an ephemeral browser context (fresh tab, in-memory)"""
        import traceback
        context = None
        try:
            # Create ephemeral context for this reply
            logger.info("🆕 Creating ephemeral browser context for reply...")
            context = await self.create_ephemeral_context()
            page = await context.new_page()

            # Quick auth sanity check
            try:
                await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(800)
                has_profile = await page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
                has_compose = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                has_login = await page.query_selector('[data-testid="LoginForm_Login_Button"]')
                if not (has_profile or has_compose) or has_login:
                    logger.error("❌ Not authenticated in ephemeral context (Safari cookies). Aborting reply.")
                    # Save a screenshot for diagnostics
                    from pathlib import Path as _P
                    _P('logs/screenshots').mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path='logs/screenshots/ephemeral_not_logged_in.png')
                    return False
            except Exception:
                pass

            logger.info(f"🎯 Navigating to tweet: {tweet_url}")
            await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            logger.info("✓ Page loaded")

            # Click reply button
            logger.info("🔍 Looking for reply button...")
            reply_button = await page.query_selector('[data-testid="reply"]')
            if not reply_button:
                logger.error("❌ Could not find reply button")
                return False
            logger.info("✓ Found reply button")

            await reply_button.click()
            await page.wait_for_timeout(1000)
            logger.info("✓ Clicked reply button")

            # Type the reply (dialog-scoped first)
            logger.info("🔍 Looking for reply text box...")
            dialog = await page.query_selector('div[role="dialog"]')
            scope = dialog or page
            selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0RichTextInputContainer"] div[contenteditable="true"]',
                'div[role="textbox"][contenteditable="true"]',
                'div[role="textbox"][data-contents="true"]',
                'div[role="textbox"]',
            ]
            reply_box = None
            for sel in selectors:
                reply_box = await scope.query_selector(sel)
                if reply_box:
                    break
            if not reply_box:
                logger.error("❌ Could not find reply text box")
                return False
            logger.info("✓ Found reply text box")

            await reply_box.click()
            await page.wait_for_timeout(300)
            await page.keyboard.type(reply_text, delay=20)
            await page.wait_for_timeout(600)
            logger.info("✓ Typed reply")

            # Click send button
            logger.info("🔍 Looking for send button...")
            send_button = await page.query_selector('[data-testid="tweetButton"]') or await scope.query_selector('[data-testid="tweetButton"]')
            if not send_button:
                logger.error("❌ Could not find send button")
                return False
            logger.info("✓ Found send button")

            await send_button.click()
            await page.wait_for_timeout(3000)  # Wait for post to complete
            logger.info("✓ Clicked send button")

            logger.info(f"✅ Reply posted successfully!")
            logger.info(f"   Reply text: {reply_text}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to post reply: {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
        finally:
            # Always close ephemeral context to free resources
            if context:
                try:
                    # Attempt to capture last page if available
                    pages = context.pages
                    if pages:
                        from pathlib import Path as _P
                        _P('logs/screenshots').mkdir(parents=True, exist_ok=True)
                        await pages[-1].screenshot(path='logs/screenshots/ephemeral_last.png')
                except Exception:
                    pass
                await context.close()
                logger.info("🧹 Closed ephemeral context")

    async def post_reply_isolated(self, tweet_url: str, reply_text: str) -> bool:
        """Post a reply using an isolated Playwright+WebKit instance (thread-safe)."""
        import traceback
        try:
            async with async_playwright() as pw:
                engine = (os.getenv('BROWSER_NAME') or os.getenv('BROWSER') or 'webkit').lower()
                if engine == 'webkit':
                    browser = await pw.webkit.launch(headless=True)
                elif engine == 'firefox':
                    browser = await pw.firefox.launch(headless=True)
                else:
                    browser = await pw.chromium.launch(headless=True)

                # Build context with cookies-only or storage
                auth_mode = (os.getenv('AUTH_MODE') or '').lower()
                storage_state = None if auth_mode == 'cookies' else (str(self.storage_state) if self.storage_state.exists() else None)
                ctx = await browser.new_context(
                    storage_state=storage_state,
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
                    ),
                )

                if auth_mode == 'cookies':
                    import json as _json
                    cookies = []
                    for p in [
                        Path("auth_data/x_cookies.json"),
                        Path("chrome_profiles/cookies/default_cookies.json"),
                        Path("config/profiles/4botbsc/storageState.json"),
                        Path("auth/4botbsc/storageState.json"),
                    ]:
                        if p.exists():
                            try:
                                data = _json.loads(p.read_text())
                                raw = data.get('cookies') if isinstance(data, dict) else data
                                for c in (raw or []):
                                    if not isinstance(c, dict):
                                        continue
                                    name = c.get('name'); value = c.get('value')
                                    if not name or value is None:
                                        continue
                                    base = {
                                        'name': name,
                                        'value': value,
                                        'path': c.get('path') or '/',
                                        'secure': True if c.get('secure') is not False else False,
                                        'httpOnly': True if c.get('httpOnly') else False,
                                        'sameSite': c.get('sameSite') or 'Lax',
                                        'expires': c.get('expires') or 0,
                                    }
                                    dom = c.get('domain') or ''
                                    variants = []
                                    if dom:
                                        variants.append({**base, 'domain': dom})
                                        if 'twitter.com' in dom and 'x.com' not in dom:
                                            variants.append({**base, 'domain': dom.replace('twitter.com','x.com')})
                                    else:
                                        variants.append({**base, 'url': 'https://x.com'})
                                    if not any((v.get('domain') or '').endswith('x.com') for v in variants):
                                        variants.append({**base, 'domain': '.x.com'})
                                    cookies.extend(variants)
                            except Exception:
                                pass
                    # Deduplicate and add
                    uniq = {}
                    for c in cookies:
                        key = (c['name'], c.get('domain') or c.get('url',''), c.get('path','/'))
                        uniq[key] = c
                    norm = list(uniq.values())
                    if norm:
                        await ctx.add_cookies(norm)

                page = await ctx.new_page()
                await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(1200)
                reply_btn = await page.query_selector('[data-testid="reply"]')
                if not reply_btn:
                    await ctx.close(); await browser.close(); return False
                await reply_btn.click(); await page.wait_for_timeout(800)
                dlg = await page.query_selector('div[role="dialog"]'); scope = dlg or page
                box = None
                for sel in ['[data-testid="tweetTextarea_0"]', '[data-testid="tweetTextarea_0RichTextInputContainer"] div[contenteditable="true"]', 'div[role="textbox"][contenteditable="true"]', 'div[role="textbox"]']:
                    box = await scope.query_selector(sel)
                    if box:
                        break
                if not box:
                    await ctx.close(); await browser.close(); return False
                await box.click(); await page.keyboard.type(reply_text, delay=20); await page.wait_for_timeout(600)
                send = await (page.query_selector('[data-testid="tweetButton"]') or scope.query_selector('[data-testid="tweetButton"]'))
                if send:
                    disabled = await send.get_attribute('aria-disabled')
                    if disabled != 'true':
                        await send.click()
                    else:
                        try:
                            await page.keyboard.press('Meta+Enter')
                        except Exception:
                            await page.keyboard.press('Control+Enter')
                else:
                    try:
                        await page.keyboard.press('Meta+Enter')
                    except Exception:
                        await page.keyboard.press('Control+Enter')
                await page.wait_for_timeout(2000)
                await ctx.close(); await browser.close(); return True
        except Exception as e:
            logger.error(f"❌ Isolated post failed: {e}")
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

        try:
            # Run isolated WebKit posting synchronously in this thread
            success = asyncio.run(self.post_reply_isolated(post_url, reply_text))

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
        if self.playwright:
            await self.playwright.stop()
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
