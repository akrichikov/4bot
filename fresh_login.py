#!/usr/bin/env python3
"""
Fresh login script - Opens browser for manual login and saves authentication
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

async def fresh_login():
    """Perform fresh login and save authentication state"""

    print("╔════════════════════════════════════════════════════════════╗")
    print("║          4bot Fresh Authentication Setup                  ║")
    print("║                                                            ║")
    print("║  A browser window will open. Please:                      ║")
    print("║  1. Login to X/Twitter with: 4botbsc@gmail.com           ║")
    print("║  2. Complete any 2FA/verification if prompted             ║")
    print("║  3. Wait for the home timeline to fully load              ║")
    print("║  4. Press ENTER in this terminal to save cookies          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    playwright = await async_playwright().start()

    # Launch visible browser
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
        ]
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    page = await context.new_page()

    # Navigate to login page
    print("🌐 Opening X/Twitter login page...")
    await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")

    # Wait for user to complete login
    print("\n⏳ Waiting for you to complete login...")
    print("   👉 After logging in successfully, press ENTER here")
    input()

    # Give a moment for any final page loads
    print("\n⏳ Waiting 5 seconds for page to stabilize...")
    await page.wait_for_timeout(5000)

    # Check if we're actually logged in
    current_url = page.url
    print(f"\n📍 Current URL: {current_url}")

    if "login" in current_url or "flow" in current_url:
        print("❌ Still on login page - authentication may not be complete")
        print("   Please ensure you've completed login and are viewing the home timeline")
        response = input("\n   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            await browser.close()
            await playwright.stop()
            return False

    # Save storage state
    storage_state_path = Path("config/profiles/4botbsc/storageState.json")
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)

    storage_state = await context.storage_state()

    with open(storage_state_path, 'w') as f:
        json.dump(storage_state, f, indent=2)

    # Also save to auth/4botbsc for compatibility
    auth_state_path = Path("auth/4botbsc/storageState.json")
    auth_state_path.parent.mkdir(parents=True, exist_ok=True)

    with open(auth_state_path, 'w') as f:
        json.dump(storage_state, f, indent=2)

    cookies = storage_state.get("cookies", [])
    auth_cookie = next((c for c in cookies if c["name"] == "auth_token"), None)
    ct0_cookie = next((c for c in cookies if c["name"] == "ct0"), None)

    print(f"\n✅ Authentication saved!")
    print(f"   📁 Primary: {storage_state_path}")
    print(f"   📁 Backup: {auth_state_path}")
    print(f"   🍪 Total cookies: {len(cookies)}")
    print(f"   🔑 auth_token: {'✅ Present' if auth_cookie else '❌ Missing'}")
    print(f"   🔑 ct0 (CSRF): {'✅ Present' if ct0_cookie else '❌ Missing'}")

    if auth_cookie:
        # Check expiration
        expires = auth_cookie.get("expires", 0)
        if expires > 0:
            expiry_date = datetime.fromtimestamp(expires)
            print(f"   📅 auth_token expires: {expiry_date}")

    await browser.close()
    await playwright.stop()

    if auth_cookie and ct0_cookie:
        print("\n🎉 Success! Authentication is ready for use.")
        print("\nNext steps:")
        print("  1. Test with: python3 verify_auth.py")
        print("  2. Run CZ scripts with fresh authentication")
        return True
    else:
        print("\n⚠️  Warning: Critical cookies may be missing")
        print("   You may need to try logging in again")
        return False

if __name__ == "__main__":
    result = asyncio.run(fresh_login())
    exit(0 if result else 1)
