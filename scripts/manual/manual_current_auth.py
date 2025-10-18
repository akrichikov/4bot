#!/usr/bin/env python3
"""Quick test to verify if current cookies provide valid authentication."""
import asyncio
from typing import Any as _Moved
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_auth():
    storage_path = Path("/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json")

    if not storage_path.exists():
        print(f"❌ Storage file not found: {storage_path}")
        return False

    with open(storage_path) as f:
        storage = json.load(f)
        cookie_count = len(storage.get("cookies", []))
        print(f"📦 Loaded {cookie_count} cookies from storageState.json")

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=False)
        context = await browser.new_context(storage_state=str(storage_path))
        page = await context.new_page()

        print("🌐 Navigating to X.com home...")
        try:
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # Wait for page to settle
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            await browser.close()
            return False

        # Check for logged-in indicators
        print("\n🔍 Checking authentication status...")

        # Check 1: Profile link
        try:
            profile_link = page.locator("a[data-testid='AppTabBar_Profile_Link']")
            if await profile_link.count() > 0:
                print("✅ Profile link found - AUTHENTICATED")
                await browser.close()
                return True
        except Exception as e:
            print(f"⚠️  Profile link check failed: {e}")

        # Check 2: Compose button
        try:
            compose = page.locator("a[href='/compose/post']")
            if await compose.count() > 0:
                print("✅ Compose button found - AUTHENTICATED")
                await browser.close()
                return True
        except Exception as e:
            print(f"⚠️  Compose button check failed: {e}")

        # Check 3: Tweet composer textbox
        try:
            composer = page.locator("div[role='textbox'][data-testid='tweetTextarea_0']")
            if await composer.count() > 0:
                print("✅ Tweet composer found - AUTHENTICATED")
                await browser.close()
                return True
        except Exception as e:
            print(f"⚠️  Tweet composer check failed: {e}")

        # Check 4: Look for login button (indicates NOT logged in)
        try:
            login_button = page.locator("a[href='/login']")
            if await login_button.count() > 0:
                print("❌ Login button found - NOT AUTHENTICATED")

                # Take screenshot for debugging
                screenshot_path = "/Users/doctordre/projects/4bot/Docs/status/diagnostics/auth_test_screenshot.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved: {screenshot_path}")

                await browser.close()
                return False
        except Exception as e:
            print(f"⚠️  Login button check failed: {e}")

        print("❓ Unable to determine authentication status")

        # Take screenshot anyway
        screenshot_path = "/Users/doctordre/projects/4bot/Docs/status/diagnostics/auth_test_unknown.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")

        # Keep browser open for 10 seconds for manual inspection
        print("\n⏳ Keeping browser open for 10 seconds for manual inspection...")
        await asyncio.sleep(10)

        await browser.close()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_auth())
    exit(0 if result else 1)
