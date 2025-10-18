#!/usr/bin/env python3
"""Reply to a specific tweet mention (Safari/WebKit headless, in-memory)."""
import asyncio
from typing import Any as _Moved
import json
from pathlib import Path
import os
from xbot.profiles import storage_state_path
from typing import List, Dict, Any
from playwright.async_api import async_playwright


from xbot.cookies import load_cookies_best_effort


def _normalize_cookies(cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm: List[Dict[str, Any]] = []
    for c in cookies:
        try:
            name = c.get('name'); value = c.get('value')
            if not name or value is None:
                continue
            domain = (c.get('domain') or '')
            path = c.get('path') or '/'
            secure = True if c.get('secure') is not False else False
            httpOnly = True if c.get('httpOnly') else False
            sameSite = c.get('sameSite') or 'Lax'
            expires = c.get('expires') or 0

            base = {
                'name': name,
                'value': value,
                'path': path,
                'secure': secure,
                'httpOnly': httpOnly,
                'sameSite': sameSite,
                'expires': expires,
            }

            # Prefer domain .x.com; duplicate twitter.com cookies for x.com
            candidates = []
            if domain:
                candidates.append({**base, 'domain': domain})
                if 'twitter.com' in domain and 'x.com' not in domain:
                    candidates.append({**base, 'domain': domain.replace('twitter.com', 'x.com')})
            else:
                # Fallback to url form
                candidates.append({**base, 'url': 'https://x.com'})

            # Ensure we include a direct x.com version
            if not any((c.get('domain') or '').endswith('x.com') for c in candidates):
                candidates.append({**base, 'domain': '.x.com'})

            norm.extend(candidates)
        except Exception:
            continue
    # Deduplicate by (name, domain, path)
    seen = set(); dedup = []
    for c in norm:
        key = (c['name'], c.get('domain') or c.get('url',''), c.get('path','/'))
        if key in seen:
            continue
        seen.add(key); dedup.append(c)
    return dedup


async def reply_to_tweet(tweet_url: str, response_text: str) -> bool:
    print(f"🎯 Replying to: {tweet_url}")
    print(f"💬 Response: {response_text}")

    cookies = _normalize_cookies(load_cookies_best_effort(profile="4botbsc"))
    profile = os.environ.get("PROFILE", "4botbsc")
    storage_state_path = storage_state_path(profile)

    async with async_playwright() as p:
        # Safari/WebKit headless in-memory session
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            storage_state=(str(storage_state_path) if storage_state_path.exists() else None),
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
        )
        if not storage_state_path.exists() and cookies:
            try:
                await context.add_cookies(cookies)
            except Exception:
                pass
        page = await context.new_page()

        # Navigate to the tweet
        print("🌐 Loading tweet...")
        await page.goto(tweet_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Click reply button
        print("🔘 Clicking reply button...")
        try:
            reply_button = await page.wait_for_selector('[data-testid="reply"]', timeout=10000)
            await reply_button.click()
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"❌ Could not find reply button: {e}")
            Path("Docs/status/diagnostics").mkdir(parents=True, exist_ok=True)
            await page.screenshot(path="Docs/status/diagnostics/mention_reply_error.png")
            await browser.close()
            return False

        # Type the response
        print("⌨️  Typing response...")
        try:
            # Fallbacks for text area (dialog-scoped preferred)
            dialog = await page.query_selector('div[role="dialog"]')
            scope = dialog or page
            selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0RichTextInputContainer"] div[contenteditable="true"]',
                'div[role="textbox"][contenteditable="true"]',
                'div[role="textbox"][data-contents="true"]',
                'div[role="textbox"]',
            ]
            text_area = None
            for sel in selectors:
                text_area = await scope.query_selector(sel)
                if text_area:
                    break
            if not text_area:
                # As last resort, wait for any textbox
                text_area = await scope.wait_for_selector('div[role="textbox"]', timeout=5000)
            await text_area.click()
            await asyncio.sleep(0.5)

            # Type character by character for human-like behavior
            for char in response_text:
                await page.keyboard.type(char)
                await asyncio.sleep(0.03)

            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Could not type response: {e}")
            await page.screenshot(path="Docs/status/diagnostics/mention_typing_error.png")
            await browser.close()
            return False

        # Submit the reply
        print("📤 Submitting reply...")
        try:
            # Try send button first
            send_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                'div[role="dialog"] [data-testid="tweetButton"]',
            ]
            sent = False
            for sel in send_selectors:
                btn = await page.query_selector(sel)
                if btn:
                    disabled = await btn.get_attribute('aria-disabled')
                    if disabled != 'true':
                        await btn.click()
                        sent = True
                        break
            if not sent:
                # Keyboard shortcut (try Command+Enter then Control+Enter)
                try:
                    await page.keyboard.press('Meta+Enter')
                except Exception:
                    await page.keyboard.press('Control+Enter')
            await asyncio.sleep(3)

            # Verify submission
            success = True
            print("✅ Reply submitted successfully!")

        except Exception as e:
            print(f"⚠️  Initial submit path failed: {e}")
            Path("Docs/status/diagnostics").mkdir(parents=True, exist_ok=True)
            await page.screenshot(path="Docs/status/diagnostics/mention_submit_error.png")
            success = False

        # Keep browser open for a moment to see result
        print("⏳ Waiting 5 seconds to verify...")
        await asyncio.sleep(5)

        await browser.close()
        return success

if __name__ == "__main__":
    tweet_url = "https://x.com/krichikov10228/status/1978870565835542864"
    response = "4. BUIDL > FUD"
    success = asyncio.run(reply_to_tweet(tweet_url, response))
    exit(0 if success else 1)
