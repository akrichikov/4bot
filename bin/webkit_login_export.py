from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page


PROFILE_NAME = os.getenv("PROFILE", "4botbsc")
ROOT = Path(__file__).resolve().parents[1]
STORAGE_OUT = ROOT / "config/profiles" / PROFILE_NAME / "storageState.json"
STORAGE_OUT.parent.mkdir(parents=True, exist_ok=True)


USERNAME = os.getenv("X_USER") or os.getenv("x_user") or os.getenv("USERNAME")
PASSWORD = os.getenv("X_PASSWORD") or os.getenv("x_passwd") or os.getenv("x_password")
TOTP_SECRET = os.getenv("X_TOTP_SECRET") or os.getenv("TOTP_SECRET")


async def is_logged_in(page: Page) -> bool:
    try:
        loc = await page.query_selector("a[aria-label='Profile'], a[aria-label='Profile menu']")
        return loc is not None
    except Exception:
        return False


async def fill_username(page: Page, username: str) -> None:
    # Some flows require typing into a different field twice.
    for sel in (
        "input[autocomplete='username']",
        "input[name='text']",
    ):
        try:
            inp = await page.wait_for_selector(sel, timeout=8000)
            await inp.fill(username)
            break
        except Exception:
            continue
    for bsel in (
        "div[role='button'][data-testid='ocfEnterTextNextButton']",
        "div[role='button'][data-testid='LoginForm_Login_Button']",
        "div[role='button'][data-testid='next_button']",
        "div[role='button']",
    ):
        try:
            btn = await page.query_selector(bsel)
            if btn:
                await btn.click()
                return
        except Exception:
            pass
    await page.keyboard.press("Enter")


async def fill_password(page: Page, password: str) -> None:
    # Sometimes X prompts again for handle/email before password
    try:
        sel_pw = "input[name='password'], input[autocomplete='current-password']"
        inp = await page.wait_for_selector(sel_pw, timeout=12000)
    except Exception:
        # fill username again if challenge appeared
        try:
            inp_user = await page.wait_for_selector("input[name='text']", timeout=8000)
            await inp_user.fill(USERNAME)
            await page.keyboard.press("Enter")
            inp = await page.wait_for_selector("input[name='password']", timeout=12000)
        except Exception:
            raise
    await inp.fill(password)
    for bsel in (
        "div[role='button'][data-testid='LoginForm_Submit_Button']",
        "div[role='button'][data-testid='LoginForm_Login_Button']",
        "div[role='button']",
    ):
        try:
            btn = await page.query_selector(bsel)
            if btn:
                await btn.click()
                return
        except Exception:
            pass
    await page.keyboard.press("Enter")


async def maybe_fill_2fa(page: Page, totp_secret: Optional[str]) -> None:
    if not totp_secret:
        return
    try:
        import pyotp  # type: ignore
        code = pyotp.TOTP(totp_secret).now()
    except Exception:
        return
    try:
        sel = "input[name='text'][inputmode='numeric']"
        box = await page.wait_for_selector(sel, timeout=8000)
        await box.fill(code)
        await page.keyboard.press("Enter")
    except Exception:
        pass


async def start_google_sso(page: Page, ctx) -> Page:
    # Try clicking the Google SSO button and capture popup or same-page nav
    candidates = (
        "div[role='button']:has-text('Sign in with Google')",
        "div[role='button']:has-text('Continue with Google')",
        "button:has-text('Sign in with Google')",
        "button:has-text('Continue with Google')",
        "text=Sign in with Google",
        "text=Continue with Google",
    )
    btn = None
    for sel in candidates:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                btn = loc.first
                break
        except Exception:
            continue
    if not btn:
        # Sometimes a generic provider list exists; try any button with 'Google'
        loc = page.locator("div[role='button']:has-text('Google'), button:has-text('Google')")
        if await loc.count() > 0:
            btn = loc.first
    if not btn:
        raise RuntimeError("Google SSO button not found")

    google_page: Page | None = None
    try:
        async with ctx.expect_page(timeout=5000) as ev:
            await btn.click()
        google_page = await ev.value
    except Exception:
        # Might be same-page
        await btn.click()
        google_page = page

    # If account chooser appears, proceed to login form
    try:
        await google_page.wait_for_load_state("domcontentloaded", timeout=20000)
    except Exception:
        pass
    return google_page


async def google_login_flow(google_page: Page, username: str, password: str) -> None:
    # Handle account chooser
    try:
        # Click "Use another account" if presented
        chooser = google_page.locator("text=Use another account")
        if await chooser.count() > 0:
            await chooser.first.click()
    except Exception:
        pass

    # Email step
    for sel in ("input[type='email'][name='identifier']", "input[type='email']", "input#identifierId"):
        try:
            inp = await google_page.wait_for_selector(sel, timeout=12000)
            await inp.fill(username)
            break
        except Exception:
            continue
    # Next button
    for b in ("#identifierNext button", "button:has-text('Next')", "div[role='button']:has-text('Next')"):
        try:
            btn = google_page.locator(b)
            if await btn.count() > 0:
                await btn.first.click()
                break
        except Exception:
            continue

    # Password step
    for sel in ("input[type='password'][name='Passwd']", "input[type='password']", "input[name='password']"):
        try:
            pwd = await google_page.wait_for_selector(sel, timeout=15000)
            await pwd.fill(password)
            break
        except Exception:
            continue
    # Next
    for b in ("#passwordNext button", "button:has-text('Next')", "div[role='button']:has-text('Next')"):
        try:
            btn = google_page.locator(b)
            if await btn.count() > 0:
                await btn.first.click()
                break
        except Exception:
            continue

    # Wait some time for redirect back to x.com
    for _ in range(40):
        try:
            url = google_page.url
            if "x.com" in url or "twitter.com" in url:
                break
        except Exception:
            pass
        await google_page.wait_for_timeout(1000)


async def main() -> None:
    if not USERNAME or not PASSWORD:
        print("[warn] X_USER/X_PASSWORD not set; will try cookie injection if needed.")

    async with async_playwright() as pw:
        # Use WebKit (Safari engine)
        browser = await pw.webkit.launch(headless=False)  # visible for reliability
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        try:
            await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
        except Exception:
            pass
        login_ok = await is_logged_in(page)
        # Prefer Google SSO if available
        if not login_ok and USERNAME and PASSWORD:
            try:
                g = await start_google_sso(page, ctx)
                await google_login_flow(g, USERNAME, PASSWORD)
                # After SSO, the original page should reflect logged-in state
                for _ in range(20):
                    if await is_logged_in(page):
                        login_ok = True
                        break
                    await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[warn] Google SSO flow not completed: {e}")
        # Fallback to username/password (if any)
        if not login_ok and USERNAME and PASSWORD:
            try:
                await fill_username(page, USERNAME)
                await fill_password(page, PASSWORD)
                await maybe_fill_2fa(page, TOTP_SECRET)
            except Exception as e:
                print(f"[warn] Credential login flow not completed: {e}")
        # wait for login or try cookie injection
        for _ in range(30):
            if await is_logged_in(page):
                login_ok = True
                break
            await page.wait_for_timeout(1000)
        if not login_ok:
            # Fallback: inject cookies/tokens from exports
            try:
                import json
                cookies_path = ROOT / "auth_data/x_cookies.json"
                if cookies_path.exists():
                    data = json.loads(cookies_path.read_text())
                    toks = []
                    for c in data:
                        if not isinstance(c, dict):
                            continue
                        dom = c.get("domain") or ""
                        if "x.com" not in dom and "twitter.com" not in dom:
                            continue
                        d = {
                            "name": c.get("name"),
                            "value": c.get("value"),
                            "domain": dom,
                            "path": c.get("path") or "/",
                            "secure": bool(c.get("secure", True)),
                            "httpOnly": bool(c.get("httpOnly", False)),
                        }
                        if c.get("expires", -1) and c["expires"] > 0:
                            d["expires"] = int(c["expires"])
                        toks.append(d)
                    if toks:
                        await ctx.add_cookies(toks)
                        await page.goto("https://x.com/home", wait_until="domcontentloaded")
                        for _ in range(10):
                            if await is_logged_in(page):
                                login_ok = True
                                break
                            await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"[warn] Cookie injection failed: {e}")
        if not login_ok:
            print("[info] Manual step required: In the opened WebKit window, click 'Sign in with Google' and complete login. This script will export storage once login is detected.")
            for i in range(600):  # up to 10 minutes
                if await is_logged_in(page):
                    login_ok = True
                    break
                await page.wait_for_timeout(1000)
        if not login_ok:
            raise SystemExit("Login failed in WebKit flow (google sso + credentials + cookies + manual)")
        # export storage state
        await ctx.storage_state(path=str(STORAGE_OUT))
        print(f"Exported storage to {STORAGE_OUT}")
        await ctx.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
