from __future__ import annotations

from asyncio import sleep
from typing import Optional

from playwright.async_api import Page

from ..config import Config
from ..human import type_text
from ..utils import jitter
import pyotp
from ..selectors import (
    LOGIN_2FA,
    LOGIN_NEXT,
    LOGIN_PASSWORD,
    LOGIN_SUBMIT,
    LOGIN_USERNAME,
    PROFILE_ANCHOR,
    GOOGLE_SIGNIN_BUTTON,
    GOOGLE_EMAIL,
    GOOGLE_EMAIL_NEXT,
    GOOGLE_PASSWORD,
    GOOGLE_PASSWORD_NEXT,
)


async def is_logged_in(page: Page) -> bool:
    try:
        if await page.locator(PROFILE_ANCHOR).first.is_visible():
            return True
    except Exception:
        pass
    try:
        from ..selectors import COMPOSE_OPENERS, FEED_COMPOSER_HITBOX
        candidates = (
            "div[role='button'][data-testid='SideNav_AccountSwitcher_Button']",
            *COMPOSE_OPENERS,
            *FEED_COMPOSER_HITBOX,
        )
        for sel in candidates:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


async def login_if_needed(page: Page, cfg: Config) -> None:
    # First attempt cookie-based session by visiting the home timeline (uses existing cookies)
    try:
        await page.goto(f"{cfg.base_url}/home", wait_until="domcontentloaded")
        if await is_logged_in(page):
            return
    except Exception:
        # proceed to interactive flow
        pass
    # Try Google SSO if requested
    if cfg.login_method == "google":
        await _login_with_google(page, cfg)
        if await is_logged_in(page):
            return
    # Try legacy and modern login flows with username/password
    for path in ("/login", "/i/flow/login"):
        try:
            await page.goto(f"{cfg.base_url}{path}", wait_until="domcontentloaded")
        except Exception:
            continue
        try:
            await _fill_username(page, cfg.username)
            await _click_first(page, LOGIN_NEXT)
            await _fill_password(page, cfg.password)
            await _click_first(page, LOGIN_SUBMIT)
            if cfg.twofa or cfg.totp_secret:
                await _maybe_fill_2fa(page, cfg.twofa, cfg.totp_secret)
            # Post-login wait and verification
            for _ in range(20):
                if await is_logged_in(page):
                    return
                await sleep(0.5)
        except Exception:
            # Try next path variant
            continue
    raise RuntimeError("Login failed: unable to locate login form or verify session.")


async def _login_with_google(page: Page, cfg: Config) -> None:
    # Navigate to login page
    try:
        await page.goto(f"{cfg.base_url}/i/flow/login", wait_until="domcontentloaded")
    except Exception:
        try:
            await page.goto(f"{cfg.base_url}/login", wait_until="domcontentloaded")
        except Exception:
            pass
    # Click the Google sign-in button (expect popup or redirect)
    clicked = False
    try:
        from ..waits import click_any_when_ready
        await click_any_when_ready(page, GOOGLE_SIGNIN_BUTTON, timeout_ms=5000)
        clicked = True
    except Exception:
        try:
            await page.locator("text=Google").first.click(timeout=3000)
            clicked = True
        except Exception:
            pass
    if not clicked:
        return
    # Handle popup or same-page flow
    popup = None
    try:
        async with page.context.expect_page() as wait_p:
            # a new page may open immediately or after redirects
            await page.wait_for_timeout(500)
        popup = await wait_p.value
    except Exception:
        # try to use current page
        popup = page
    p = popup or page
    # Fill Google email
    try:
        await p.locator(GOOGLE_EMAIL).first.fill((cfg.username or cfg.email or "").strip(), timeout=10000)
        await p.locator(GOOGLE_EMAIL_NEXT).first.click()
    except Exception:
        pass
    # Fill Google password (wait for navigation)
    try:
        await p.locator(GOOGLE_PASSWORD).first.fill((cfg.password or "").strip(), timeout=15000)
        await p.locator(GOOGLE_PASSWORD_NEXT).first.click()
    except Exception:
        pass
    # Wait a bit for session to propagate
    for _ in range(30):
        try:
            if p != page and p.is_closed():
                break
        except Exception:
            break
        await sleep(0.5)
    try:
        await page.goto(f"{cfg.base_url}/home", wait_until="domcontentloaded")
    except Exception:
        pass


async def _fill_username(page: Page, username: Optional[str]) -> None:
    if not username:
        raise ValueError("USERNAME/X_USER is not set")
    loc = page.locator(LOGIN_USERNAME).first
    try:
        await type_text(loc, username)
    except Exception:
        await loc.fill(username)


async def _fill_password(page: Page, password: Optional[str]) -> None:
    if not password:
        raise ValueError("PASSWORD/X_PASSWORD is not set")
    loc = page.locator(LOGIN_PASSWORD).first
    try:
        await type_text(loc, password)
    except Exception:
        await loc.fill(password)


async def _maybe_fill_2fa(page: Page, twofa: Optional[str], totp_secret: Optional[str]) -> None:
    code: Optional[str] = twofa
    if not code and totp_secret:
        try:
            code = pyotp.TOTP(totp_secret).now()
        except Exception:
            code = None
    if not code:
        return
    locator = page.locator(LOGIN_2FA)
    if await locator.count() > 0:
        try:
            await type_text(locator.first, code)
        except Exception:
            await locator.first.fill(code)
    await jitter(200, 400)


async def _click_first(page: Page, selector_union: str) -> None:
    await page.locator(selector_union).first.click()
