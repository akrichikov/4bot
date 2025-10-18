#!/usr/bin/env python3
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

STORAGE_PRIMARY = Path("config/profiles/4botbsc/storageState.json")
STORAGE_COMPAT  = Path("auth/4botbsc/storageState.json")

INSTRUCTIONS = """
╔════════════════════════════════════════════════════════════╗
║            SAFARI (WebKit) MANUAL LOGIN CAPTURE            ║
║                                                            ║
║  A Safari/WebKit browser window is now open.               ║
║  Please complete login to X.com in that window.            ║
║                                                            ║
║  This tool auto-detects successful login and saves         ║
║  authentication (storageState.json) for future headless    ║
║  ephemeral posting. No terminal input required.            ║
╚════════════════════════════════════════════════════════════╝
""".strip()


async def main() -> int:
    print(INSTRUCTIONS)
    STORAGE_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
    STORAGE_COMPAT.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=False)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900},
                                        user_agent=(
                                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                                            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
                                        ))
        page = await ctx.new_page()
        await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")

        # Poll for up to 12 minutes (144 * 5s)
        for i in range(144):
            await asyncio.sleep(5)
            try:
                # If we have profile or compose button, assume logged in
                prof = await page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
                comp = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                login_btn = await page.query_selector('[data-testid="LoginForm_Login_Button"]')
                if (prof or comp) and not login_btn:
                    print("✅ Detected logged-in session; saving storageState...")
                    state = await ctx.storage_state()
                    STORAGE_PRIMARY.write_text(json.dumps(state, indent=2))
                    STORAGE_COMPAT.write_text(json.dumps(state, indent=2))
                    print(f"   Saved: {STORAGE_PRIMARY}")
                    print(f"   Saved: {STORAGE_COMPAT}")
                    # small grace period
                    await asyncio.sleep(2)
                    await browser.close()
                    return 0
            except Exception:
                pass

        print("⚠️  Timeout: login not detected. Please rerun and complete login.")
        try:
            await browser.close()
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

