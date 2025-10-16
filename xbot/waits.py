from __future__ import annotations

from typing import Optional

from playwright.async_api import Locator, Page


async def wait_visible(page: Page, selector: str, timeout_ms: int = 15000) -> bool:
    loc = page.locator(selector).first
    try:
        await loc.wait_for(state="visible", timeout=timeout_ms)
        return True
    except Exception:
        try:
            return await loc.is_visible()
        except Exception:
            return False


async def wait_any_visible(page: Page, selectors: str | tuple[str, ...], timeout_ms: int = 15000) -> Optional[str]:
    if isinstance(selectors, str):
        selectors = tuple(s.strip() for s in selectors.split(",") if s.strip())
    for sel in selectors:
        if await wait_visible(page, sel, timeout_ms=timeout_ms):
            return sel
    return None


async def wait_clickable(page: Page, selector: str, timeout_ms: int = 15000) -> bool:
    loc = page.locator(selector).first
    try:
        await loc.wait_for(state="visible", timeout=timeout_ms)
        return await loc.is_enabled()
    except Exception:
        return False


async def click_when_ready(page: Page, selector: str, timeout_ms: int = 15000) -> None:
    if await wait_clickable(page, selector, timeout_ms):
        await page.locator(selector).first.click()
    else:
        raise TimeoutError(f"click_when_ready: selector not clickable: {selector}")


async def click_any_when_ready(page: Page, selectors: str | tuple[str, ...], timeout_ms: int = 15000) -> None:
    sel = await wait_any_visible(page, selectors, timeout_ms)
    if sel:
        await click_when_ready(page, sel, timeout_ms)
        return
    raise TimeoutError(f"click_any_when_ready: none clickable: {selectors}")


async def wait_count_at_least(page: Page, selector: str, n: int, timeout_ms: int = 15000) -> bool:
    loc = page.locator(selector)
    try:
        await page.wait_for_function(
            "(sel, min) => document.querySelectorAll(sel).length >= min",
            selector,
            n,
            timeout=timeout_ms,
        )
        return True
    except Exception:
        try:
            return (await loc.count()) >= n
        except Exception:
            return False
