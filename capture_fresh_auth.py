#!/usr/bin/env python3
"""
Fresh Authentication Capture - Manual login to get valid cookies
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
logger = logging.getLogger('AUTH_CAPTURE')


class FreshAuthCapture:
    """Capture fresh authentication cookies from manual login"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.storage_state_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json"
        self.backup_path = "/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState_backup.json"

    async def backup_existing(self):
        """Backup existing authentication"""
        if Path(self.storage_state_path).exists():
            with open(self.storage_state_path, 'r') as f:
                data = json.load(f)

            # Save backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState_{timestamp}.json"
            with open(backup_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"✅ Backed up existing auth to: {backup_file}")

    async def capture_auth(self):
        """Launch browser for manual authentication"""
        logger.info("🌐 Launching browser for manual authentication...")

        playwright = await async_playwright().start()

        # Launch with GUI for manual login
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security'
            ]
        )

        # Create fresh context without existing cookies
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self.page = await self.context.new_page()

        logger.info("="*60)
        logger.info("📱 MANUAL AUTHENTICATION REQUIRED")
        logger.info("="*60)
        logger.info("")
        logger.info("Please follow these steps:")
        logger.info("")
        logger.info("1. The browser will open to X.com login page")
        logger.info("2. Log in with 4botbsc@gmail.com account")
        logger.info("3. Complete any 2FA if required")
        logger.info("4. Navigate to home feed to confirm login")
        logger.info("5. Press Enter in this terminal when logged in")
        logger.info("")
        logger.info("="*60)

        # Navigate to X.com login
        await self.page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")

        # Wait for user to complete login
        input("\n✋ Press Enter when you have successfully logged in...")

        # Verify authentication
        logger.info("\n🔍 Verifying authentication...")

        # Navigate to home
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Check if authenticated
        content = await self.page.content()

        authenticated = False
        if "home" in self.page.url.lower() and "sign in" not in content.lower():
            authenticated = True
            logger.info("✅ Authentication successful!")

            # Get username
            try:
                username_element = await self.page.query_selector('[data-testid="SideNav_AccountSwitcher_Button"]')
                if username_element:
                    username_text = await username_element.text_content()
                    logger.info(f"✅ Logged in as: {username_text}")
            except:
                pass
        else:
            logger.error("❌ Authentication failed - not logged in")
            return False

        # Save authentication state
        if authenticated:
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
            for cookie in storage_state.get('cookies', []):
                if cookie['name'] in important_cookies:
                    logger.info(f"   ✓ {cookie['name']}: {'*' * 10}{cookie['value'][-10:]}")

            return True

        return False

    async def test_saved_auth(self):
        """Test the saved authentication"""
        logger.info("\n🧪 Testing saved authentication...")

        # Create new context with saved state
        test_context = await self.browser.new_context(
            storage_state=self.storage_state_path
        )

        test_page = await test_context.new_page()

        # Try to access a tweet
        test_url = "https://x.com/CryptoNobler/status/1978742203036921985"
        logger.info(f"Testing access to: {test_url}")

        await test_page.goto(test_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        content = await test_page.content()

        if "doesn't exist" in content or "something went wrong" in content.lower():
            logger.warning("⚠️ Tweet shows as unavailable with new auth")
        else:
            logger.info("✅ Tweet is accessible with new auth!")

            # Try to find reply button
            reply_button = await test_page.query_selector('[data-testid="reply"]')
            if reply_button:
                logger.info("✅ Reply button found - full access confirmed!")
            else:
                logger.warning("⚠️ Reply button not found")

        await test_context.close()

    async def run(self):
        """Main execution"""
        try:
            # Backup existing auth
            await self.backup_existing()

            # Capture new auth
            success = await self.capture_auth()

            if success:
                # Test the new auth
                await self.test_saved_auth()

                logger.info("\n" + "="*60)
                logger.info("🎉 AUTHENTICATION CAPTURE COMPLETE")
                logger.info("="*60)
                logger.info("")
                logger.info("New authentication has been saved to:")
                logger.info(f"  {self.storage_state_path}")
                logger.info("")
                logger.info("You can now run the reply scripts with fresh auth!")
                logger.info("")
            else:
                logger.error("\n❌ Authentication capture failed")

        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    capturer = FreshAuthCapture()
    await capturer.run()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║         FRESH AUTHENTICATION CAPTURE TOOL v1.0            ║
    ║                                                           ║
    ║      Manual login to capture valid authentication         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())