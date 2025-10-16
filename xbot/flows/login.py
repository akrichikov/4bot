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
    # Try legacy and modern login flows
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
