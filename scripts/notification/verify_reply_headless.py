#!/usr/bin/env python3
import asyncio
from typing import Any as _Moved
from pathlib import Path
import sys

from playwright.async_api import async_playwright

STATUS_URL = sys.argv[1] if len(sys.argv) > 1 else ""
PROFILE = "4botbsc"
STORAGE = Path("config/profiles/4botbsc/storageState.json").resolve()


async def main():
    if not STATUS_URL:
        print({"error": "usage", "hint": "verify_reply_headless.py <status_url>"})
        return 1
    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            storage_state=str(STORAGE) if STORAGE.exists() else None,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
        )
        page = await context.new_page()
        try:
            await page.goto(STATUS_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass
        # Give it a moment and scroll
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollBy(0, 400)")
        await page.wait_for_timeout(1000)

        # Look for a reply authored by @4botbsc in the thread
        # Heuristic: find any article with a user-name link to /4botbsc
        sel_author = "[data-testid='User-Name'] a[href^='/%s']" % PROFILE
        authors = await page.locator(sel_author).all()
        found = False
        for a in authors:
            try:
                href = await a.get_attribute('href')
                if href and href.strip('/').lower() == PROFILE.lower():
                    found = True
                    break
            except Exception:
                continue
        # Also try simple text search for the handle
        if not found:
            text_hit = await page.locator("text=@%s" % PROFILE).count()
            found = text_hit > 0

        print({"status_url": STATUS_URL, "reply_found": found})
        await context.close()
        await browser.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
