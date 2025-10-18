#!/usr/bin/env python3
"""Test authentication using the CORRECT storage path that xbot uses."""
import asyncio
from typing import Any as _Moved
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_auth():
    # Use the CORRECT path that xbot CLI uses
    storage_path = Path("/Users/doctordre/projects/4bot/auth/4botbsc/storageState.json")

    if not storage_path.exists():
        print(f"❌ Storage file not found: {storage_path}")
        return False

    with open(storage_path) as f:
        storage = json.load(f)
        cookie_count = len(storage.get("cookies", []))
        print(f"📦 Loaded {cookie_count} cookies from {storage_path.name}")

        # Check for auth tokens
        cookies_dict = {c['name']: c['value'][:20] + '...' for c in storage['cookies'] if c['name'] in ['auth_token', 'ct0', 'kdt', 'att']}
        print(f"🔑 Auth tokens present: {list(cookies_dict.keys())}")

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=False)
        context = await browser.new_context(storage_state=str(storage_path))
        page = await context.new_page()

        print("\n🌐 Navigating to X.com home...")
        try:
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=45000)
            print("✅ Page navigation completed")

            # Wait longer for React to render
            print("⏳ Waiting 10 seconds for React app to render...")
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            await browser.close()
            return False

        # Check for logged-in indicators
        print("\n🔍 Checking authentication status...")

        checks = [
            ("Profile link", "a[data-testid='AppTabBar_Profile_Link']"),
            ("Compose link", "a[href='/compose/post']"),
            ("Tweet composer", "div[role='textbox'][data-testid='tweetTextarea_0']"),
            ("Account switcher", "div[role='button'][data-testid='SideNav_AccountSwitcher_Button']"),
        ]

        authenticated = False
        for name, selector in checks:
            try:
                loc = page.locator(selector)
                count = await loc.count()
                if count > 0:
                    print(f"✅ {name} found ({count} elements) - AUTHENTICATED!")
                    authenticated = True
                    break
                else:
                    print(f"⚠️  {name} not found")
            except Exception as e:
                print(f"⚠️  {name} check error: {e}")

        if not authenticated:
            # Check for login button
            try:
                login_btn = page.locator("a[href='/login']")
                if await login_btn.count() > 0:
                    print("❌ Login button found - NOT AUTHENTICATED")
            except:
                pass

            # Take screenshot
            screenshot_path = "/Users/doctordre/projects/4bot/Docs/status/diagnostics/auth_correct_path_test.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")

        print("\n⏳ Keeping browser open for 15 seconds...")
        await asyncio.sleep(15)

        await browser.close()
        return authenticated

if __name__ == "__main__":
    result = asyncio.run(test_auth())
    if result:
        print("\n" + "="*70)
        print("🎉 AUTHENTICATION SUCCESS! Ready to run reply system!")
        print("="*70)
        exit(0)
    else:
        print("\n" + "="*70)
        print("❌ AUTHENTICATION FAILED - Manual login still required")
        print("="*70)
        exit(1)
