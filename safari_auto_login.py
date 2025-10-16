#!/usr/bin/env python3
"""
Safari Automated Login - Login to X.com using Safari browser
Automatically fills credentials and captures authentication
"""

import asyncio
import json
from pathlib import Path
import logging
from datetime import datetime

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('SAFARI_LOGIN')


class SafariAutoLogin:
    """Automated login using Safari (webkit) browser"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"

        # Credentials
        self.username = "4botbsc@gmail.com"
        self.password = "RLLYhEqEPM@gJ3vY"

    async def backup_existing(self):
        """Backup existing authentication"""
        if Path(self.storage_state_path).exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState_backup_{timestamp}.json"

            with open(self.storage_state_path, 'r') as f:
                data = json.load(f)

            with open(backup_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"✅ Backed up existing auth to: {backup_file}")

    async def login_to_x(self):
        """Automated login to X.com using Safari"""
        logger.info("🌐 Launching Safari browser...")

        playwright = await async_playwright().start()

        # Launch Safari (webkit)
        self.browser = await playwright.webkit.launch(
            headless=False,  # Show browser for monitoring
        )

        # Create fresh context
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )

        self.page = await self.context.new_page()

        logger.info("="*60)
        logger.info("🔐 AUTOMATED X.COM LOGIN")
        logger.info("="*60)
        logger.info(f"Username: {self.username}")
        logger.info(f"Browser: Safari (webkit)")
        logger.info("="*60)

        # Navigate to X.com login
        logger.info("\n📱 Navigating to X.com login page...")
        await self.page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Wait for username input
        logger.info("👤 Entering username...")
        try:
            # Try different possible selectors for username field
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]',
                '[data-testid="login-username"]'
            ]

            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if username_input:
                        logger.info(f"   Found username field: {selector}")
                        break
                except:
                    continue

            if not username_input:
                logger.error("❌ Could not find username input field")
                return False

            # Type username
            await username_input.click()
            await asyncio.sleep(0.5)
            await username_input.fill(self.username)
            await asyncio.sleep(1)

            # Click Next button
            logger.info("➡️  Clicking Next...")

            # Try multiple selectors for Next button
            next_button_selectors = [
                'button:has-text("Next")',
                'div[role="button"]:has-text("Next")',
                '[data-testid="ocfEnterTextNextButton"]',
                'button[type="button"]'
            ]

            clicked = False
            for selector in next_button_selectors:
                try:
                    next_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if next_button:
                        logger.info(f"   Found Next button: {selector}")
                        await next_button.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                logger.info("   Trying keyboard Enter instead...")
                await self.page.keyboard.press('Enter')

            await asyncio.sleep(4)

        except Exception as e:
            logger.error(f"Error entering username: {e}")
            return False

        # Wait for password input
        logger.info("🔑 Entering password...")
        try:
            password_selectors = [
                'input[autocomplete="current-password"]',
                'input[name="password"]',
                'input[type="password"]',
                '[data-testid="login-password"]'
            ]

            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if password_input:
                        logger.info(f"   Found password field: {selector}")
                        break
                except:
                    continue

            if not password_input:
                logger.error("❌ Could not find password input field")
                return False

            # Type password
            await password_input.click()
            await asyncio.sleep(0.5)
            await password_input.fill(self.password)
            await asyncio.sleep(1)

            # Click Log in button
            logger.info("🚀 Clicking Log in...")

            # Try multiple selectors for Log in button
            login_button_selectors = [
                'button:has-text("Log in")',
                'div[role="button"]:has-text("Log in")',
                '[data-testid="LoginForm_Login_Button"]',
                'button[type="submit"]'
            ]

            clicked = False
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if login_button:
                        logger.info(f"   Found Log in button: {selector}")
                        await login_button.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                logger.info("   Trying keyboard Enter instead...")
                await self.page.keyboard.press('Enter')

            await asyncio.sleep(6)

        except Exception as e:
            logger.error(f"Error entering password: {e}")
            return False

        # Wait for home page
        logger.info("\n⏳ Waiting for authentication...")
        await asyncio.sleep(5)

        # Check if we're on home page
        current_url = self.page.url
        logger.info(f"Current URL: {current_url}")

        if "home" in current_url.lower():
            logger.info("✅ Successfully logged in!")

            # Get username from profile
            try:
                profile_button = await self.page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]')
                if profile_button:
                    profile_text = await profile_button.text_content()
                    logger.info(f"✅ Authenticated as: {profile_text}")
            except:
                pass

            return True
        else:
            logger.warning("⚠️ Not on home page - login may have failed or require 2FA")
            logger.info("Waiting 30 seconds for manual intervention if needed...")
            await asyncio.sleep(30)

            # Check again
            current_url = self.page.url
            if "home" in current_url.lower():
                logger.info("✅ Successfully logged in after wait!")
                return True
            else:
                logger.error("❌ Login failed")
                return False

    async def save_authentication(self):
        """Save authentication state"""
        logger.info("\n💾 Saving authentication state...")

        # Get storage state
        storage_state = await self.context.storage_state()

        # Save to file
        with open(self.storage_state_path, 'w') as f:
            json.dump(storage_state, f, indent=2)

        # Report statistics
        cookie_count = len(storage_state.get('cookies', []))
        logger.info(f"✅ Saved {cookie_count} cookies to storageState.json")

        # List important cookies
        important_cookies = ['auth_token', 'ct0', 'kdt', 'twid']
        logger.info("\n🔑 Important authentication cookies:")
        for cookie in storage_state.get('cookies', []):
            if cookie['name'] in important_cookies:
                logger.info(f"   ✓ {cookie['name']}: {'*' * 10}{cookie['value'][-10:]}")

        return True

    async def test_authentication(self):
        """Test the saved authentication"""
        logger.info("\n🧪 Testing saved authentication...")

        # Create new context with saved state
        test_context = await self.browser.new_context(
            storage_state=self.storage_state_path
        )

        test_page = await test_context.new_page()

        # Test accessing a specific tweet
        test_tweets = [
            "https://x.com/CryptoNobler/status/1978742203036921985",
            "https://x.com/bitcoindata21/status/1976989902295150920"
        ]

        success_count = 0
        for test_url in test_tweets:
            logger.info(f"\n📋 Testing: {test_url}")

            await test_page.goto(test_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)

            content = await test_page.content()

            # Check if accessible
            if "doesn't exist" in content or "something went wrong" in content.lower():
                logger.warning("   ⚠️ Tweet shows as unavailable")
            else:
                logger.info("   ✅ Tweet is accessible!")

                # Check for reply button
                reply_button = await test_page.query_selector('[data-testid="reply"]')
                if reply_button:
                    logger.info("   ✅ Reply button found - full access confirmed!")
                    success_count += 1
                else:
                    logger.warning("   ⚠️ Reply button not found")

        await test_context.close()

        if success_count > 0:
            logger.info(f"\n✅ Authentication test passed! ({success_count}/{len(test_tweets)} tweets accessible)")
            return True
        else:
            logger.warning(f"\n⚠️ Authentication test failed - no tweets accessible")
            return False

    async def run(self):
        """Main execution"""
        try:
            # Backup existing auth
            await self.backup_existing()

            # Login to X
            login_success = await self.login_to_x()

            if not login_success:
                logger.error("\n❌ Login failed!")
                return False

            # Save authentication
            await self.save_authentication()

            # Test authentication
            test_success = await self.test_authentication()

            if test_success:
                logger.info("\n" + "="*60)
                logger.info("🎉 AUTHENTICATION CAPTURE COMPLETE!")
                logger.info("="*60)
                logger.info("")
                logger.info("✅ Successfully logged in with Safari")
                logger.info("✅ Authentication saved to storageState.json")
                logger.info("✅ Authentication validated with test tweets")
                logger.info("")
                logger.info("🚀 Ready to run reply system!")
                logger.info("")
                logger.info("Next: python cz_available_tweets_reply.py")
                logger.info("="*60)
            else:
                logger.warning("\n⚠️ Login succeeded but authentication test failed")

            # Keep browser open for 10 seconds
            logger.info("\nBrowser will close in 10 seconds...")
            await asyncio.sleep(10)

            return test_success

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    login_system = SafariAutoLogin()
    success = await login_system.run()

    if success:
        logger.info("\n✅ All systems ready!")
    else:
        logger.error("\n❌ Authentication setup failed")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          SAFARI AUTOMATED LOGIN v1.0                      ║
    ║                                                           ║
    ║       Automatic authentication capture using Safari       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())