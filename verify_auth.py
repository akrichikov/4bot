#!/usr/bin/env python3
"""
Quick authentication verification script
Checks if stored authentication cookies are valid
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def verify_auth():
    """Verify X/Twitter authentication"""
    storage_state = Path("config/profiles/4botbsc/storageState.json")

    if not storage_state.exists():
        print(f"❌ Storage state not found: {storage_state}")
        return False

    # Load and check cookies
    with open(storage_state) as f:
        state = json.load(f)

    cookies = state.get("cookies", [])
    auth_cookie = next((c for c in cookies if c["name"] == "auth_token"), None)
    ct0_cookie = next((c for c in cookies if c["name"] == "ct0"), None)

    print(f"📋 Found {len(cookies)} total cookies")
    print(f"   auth_token: {'✅ Present' if auth_cookie else '❌ Missing'}")
    print(f"   ct0 (CSRF): {'✅ Present' if ct0_cookie else '❌ Missing'}")

    if not auth_cookie or not ct0_cookie:
        print("❌ Critical authentication cookies missing")
        return False

    # Test with browser
    print("\n🌐 Testing authentication with browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)

    context = await browser.new_context(
        storage_state=str(storage_state),
        viewport={"width": 1920, "height": 1080}
    )

    page = await context.new_page()

    try:
        # Navigate to X/Twitter home
        print("   Navigating to https://x.com/home...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Check if we're logged in by looking for user-specific elements
        is_logged_in = False

        # Try to find the compose tweet button (only visible when logged in)
        compose_button = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
        if compose_button:
            is_logged_in = True
            print("   ✅ Found compose tweet button - logged in!")

        # Try to find profile link
        if not is_logged_in:
            profile_link = await page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
            if profile_link:
                is_logged_in = True
                print("   ✅ Found profile link - logged in!")

        # Check for login form (indicates NOT logged in)
        login_form = await page.query_selector('[data-testid="LoginForm_Login_Button"]')
        if login_form:
            is_logged_in = False
            print("   ❌ Found login form - NOT logged in")

        # Take screenshot for debugging
        screenshot_path = Path("auth_verification.png")
        await page.screenshot(path=str(screenshot_path))
        print(f"   📸 Screenshot saved: {screenshot_path}")

        if is_logged_in:
            print("\n✅ Authentication VALID - User is logged in")
            return True
        else:
            print("\n❌ Authentication INVALID - User is NOT logged in")
            return False

    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        return False
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    result = asyncio.run(verify_auth())
    exit(0 if result else 1)
