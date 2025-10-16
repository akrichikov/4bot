#!/usr/bin/env python3
"""Manual Google SSO login with proper wait times - opens visible browser for user completion."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def manual_google_login():
    storage_path = Path("/Users/doctordre/projects/4bot/config/profiles/4botbsc/storageState.json")

    print("🚀 Starting manual Google SSO login for 4botbsc...")
    print("📧 Email: 4botbsc@gmail.com")
    print("🔒 Password: RLLYhEqEPM@gJ3vY")
    print()

    async with async_playwright() as p:
        # Launch visible Safari browser
        browser = await p.webkit.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("🌐 Navigating to X.com login page...")
        await page.goto("https://x.com/i/flow/login", timeout=60000)

        print("\n⏳ Waiting 5 seconds for page to load...")
        await asyncio.sleep(5)

        print("\n" + "="*70)
        print("👤 MANUAL STEPS REQUIRED:")
        print("="*70)
        print("1. Click 'Sign in with Google' button")
        print("2. Enter email: 4botbsc@gmail.com")
        print("3. Enter password: RLLYhEqEPM@gJ3vY")
        print("4. Complete any 2FA/verification if prompted")
        print("5. Wait for login to complete and X.com home page to load")
        print("6. You should see your profile/timeline")
        print("="*70)
        print()
        print("⏰ This script will wait up to 3 minutes for you to complete login...")
        print("   Once logged in, cookies will be automatically saved.")
        print()

        # Wait up to 3 minutes for user to complete login
        login_successful = False
        for i in range(36):  # 36 * 5 seconds = 3 minutes
            await asyncio.sleep(5)

            # Check if logged in
            try:
                # Check for profile link
                profile_link = page.locator("a[data-testid='AppTabBar_Profile_Link']")
                if await profile_link.count() > 0:
                    login_successful = True
                    break

                # Check for compose button
                compose = page.locator("a[href='/compose/post']")
                if await compose.count() > 0:
                    login_successful = True
                    break

                # Check for tweet composer
                composer = page.locator("div[role='textbox'][data-testid='tweetTextarea_0']")
                if await composer.count() > 0:
                    login_successful = True
                    break

                if (i + 1) % 6 == 0:  # Every 30 seconds
                    elapsed = (i + 1) * 5
                    remaining = 180 - elapsed
                    print(f"⏳ Still waiting... ({elapsed}s elapsed, {remaining}s remaining)")

            except Exception as e:
                continue

        if login_successful:
            print("\n" + "="*70)
            print("✅ LOGIN SUCCESSFUL!")
            print("="*70)

            # Save cookies
            print(f"\n💾 Saving authentication to: {storage_path}")
            storage_state = await context.storage_state()

            # Create backup of old cookies
            if storage_path.exists():
                backup_path = storage_path.parent / f"storageState_backup_{asyncio.get_event_loop().time():.0f}.json"
                import shutil
                shutil.copy(storage_path, backup_path)
                print(f"📦 Old cookies backed up to: {backup_path.name}")

            # Ensure directory exists
            storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Save new cookies
            with open(storage_path, 'w') as f:
                json.dump(storage_state, f, indent=2)

            cookie_count = len(storage_state.get('cookies', []))
            print(f"✅ Saved {cookie_count} cookies")

            # Verify the cookies work
            print("\n🔍 Verifying authentication...")
            await asyncio.sleep(2)

            # Navigate to home to confirm
            try:
                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Final verification
                profile_link = page.locator("a[data-testid='AppTabBar_Profile_Link']")
                if await profile_link.count() > 0:
                    print("✅ Authentication verified - ready to post replies!")
                    print("\n📝 Next step: Run the CZ reply system:")
                    print("   python /Users/doctordre/projects/4bot/cz_available_tweets_reply.py")
                else:
                    print("⚠️  Authentication saved but verification inconclusive")

            except Exception as e:
                print(f"⚠️  Verification navigation failed: {e}")

            print("\n⏳ Keeping browser open for 10 seconds for final inspection...")
            await asyncio.sleep(10)

        else:
            print("\n" + "="*70)
            print("❌ LOGIN TIMEOUT")
            print("="*70)
            print("Login was not completed within 3 minutes.")
            print("Please try again and complete the login process faster.")
            print("\n⏳ Keeping browser open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)

        await browser.close()
        return login_successful

if __name__ == "__main__":
    success = asyncio.run(manual_google_login())
    exit(0 if success else 1)
