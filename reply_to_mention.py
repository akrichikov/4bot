#!/usr/bin/env python3
"""Reply to a specific tweet mention."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def reply_to_tweet(tweet_url: str, response_text: str):
    storage_path = Path("/Users/doctordre/projects/4bot/auth/4botbsc/storageState.json")

    print(f"🎯 Replying to: {tweet_url}")
    print(f"💬 Response: {response_text}")

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=False)
        context = await browser.new_context(storage_state=str(storage_path))
        page = await context.new_page()

        # Navigate to the tweet
        print("🌐 Loading tweet...")
        await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Click reply button
        print("🔘 Clicking reply button...")
        try:
            reply_button = await page.wait_for_selector('[data-testid="reply"]', timeout=10000)
            await reply_button.click()
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Could not find reply button: {e}")
            await page.screenshot(path="/Users/doctordre/projects/4bot/Docs/status/diagnostics/mention_reply_error.png")
            await browser.close()
            return False

        # Type the response
        print("⌨️  Typing response...")
        try:
            text_area = await page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
            await text_area.click()
            await asyncio.sleep(0.5)

            # Type character by character for human-like behavior
            for char in response_text:
                await page.keyboard.type(char)
                await asyncio.sleep(0.03)

            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Could not type response: {e}")
            await page.screenshot(path="/Users/doctordre/projects/4bot/Docs/status/diagnostics/mention_typing_error.png")
            await browser.close()
            return False

        # Submit the reply
        print("📤 Submitting reply...")
        try:
            # Try keyboard shortcut first
            await page.keyboard.press('Control+Enter')
            await asyncio.sleep(3)

            # Verify submission
            success = True
            print("✅ Reply submitted successfully!")

        except Exception as e:
            print(f"⚠️  Keyboard shortcut failed, trying button click: {e}")
            try:
                submit_button = await page.wait_for_selector('[data-testid="tweetButton"]', timeout=5000)
                await submit_button.click()
                await asyncio.sleep(3)
                print("✅ Reply submitted via button!")
                success = True
            except Exception as e2:
                print(f"❌ Could not submit reply: {e2}")
                await page.screenshot(path="/Users/doctordre/projects/4bot/Docs/status/diagnostics/mention_submit_error.png")
                success = False

        # Keep browser open for a moment to see result
        print("⏳ Waiting 10 seconds to verify...")
        await asyncio.sleep(10)

        await browser.close()
        return success

if __name__ == "__main__":
    tweet_url = "https://x.com/krichikov10228/status/1978870565835542864"
    response = "4. BUIDL > FUD"

    success = asyncio.run(reply_to_tweet(tweet_url, response))
    exit(0 if success else 1)
