from __future__ import annotations

from typing import Optional, Tuple
from .utils import normalize_text
import re

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


async def wait_toast(page: Page, selectors: str | tuple[str, ...], pattern: str = r"sent|posted|reply|message", timeout_ms: int = 5000) -> bool:
    if isinstance(selectors, str):
        selectors = tuple(s.strip() for s in selectors.split(",") if s.strip())
    regex = re.compile(pattern, re.IGNORECASE)
    for sel in selectors:
        try:
            await page.locator(sel, has_text=regex).first.wait_for(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def parse_status_id(url: str) -> Optional[str]:
    try:
        import re
        m = re.search(r"/status/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/status/(\d+)$", url)
        if m:
            return m.group(1)
        m = re.search(r"/i/web/status/(\d+)", url)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


async def extract_status_id_from_article(page: Page, article_locator_selector: str) -> Optional[str]:
    try:
        # find first anchor with /status/ inside the article
        anchor = page.locator(article_locator_selector).locator("a[href*='/status/']").first
        href = await anchor.get_attribute("href")
        if href:
            return parse_status_id(href)
    except Exception:
        return None
    return None


async def extract_status_id_from_profile(page: Page, handle: str, text: str, max_articles: int = 20, timeout_ms: int = 6000) -> Optional[str]:
    try:
        arts = page.locator("article").filter(
            has=page.locator(f"a[href='/{handle}']"),
            has_text=text,
        )
        n = await arts.count()
        n = min(n, max_articles)
        for i in range(n):
            art = arts.nth(i)
            try:
                await art.wait_for(timeout=timeout_ms)
                href = await art.locator("a[href*='/status/']").first.get_attribute("href")
                if href:
                    sid = parse_status_id(href)
                    if sid:
                        return sid
            except Exception:
                continue
        return None
    except Exception:
        return None


async def verify_status_context(page: Page, status_id: str, timeout_ms: int = 4000) -> bool:
    try:
        # quick URL check
        url = page.url
        if status_id and status_id in url:
            return True
        # anchor presence
        sel = f"a[href*='/status/{status_id}']"
        await page.locator(sel).first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False


async def extract_reply_status_id_from_thread(page: Page, handle: str, text: str, timeout_ms: int = 6000) -> Optional[str]:
    try:
        # article authored by handle with the reply text
        art = page.locator("article").filter(
            has=page.locator(f"a[href='/{handle}']"),
            has_text=text,
        ).first
        await art.wait_for(timeout=timeout_ms)
        href = await art.locator("a[href*='/status/']").first.get_attribute("href")
        if href:
            return parse_status_id(href)
    except Exception:
        return None
    return None


async def extract_reply_status_id_from_with_replies(page: Page, base_url: str, handle: str, text: str, max_articles: int = 20, timeout_ms: int = 6000) -> Optional[str]:
    try:
        await page.goto(f"{base_url.rstrip('/')}/{handle}/with_replies", wait_until="domcontentloaded")
        arts = page.locator("article").filter(
            has=page.locator(f"a[href='/{handle}']"),
            has_text=text,
        )
        n = await arts.count()
        n = min(n, max_articles)
        for i in range(n):
            art = arts.nth(i)
            try:
                await art.wait_for(timeout=timeout_ms)
                href = await art.locator("a[href*='/status/']").first.get_attribute("href")
                if href:
                    sid = parse_status_id(href)
                    if sid:
                        return sid
            except Exception:
                continue
        return None
    except Exception:
        return None


async def wait_text_in(page: Page, selectors: str | tuple[str, ...], text: str, timeout_ms: int = 6000) -> bool:
    if isinstance(selectors, str):
        selectors = tuple(s.strip() for s in selectors.split(",") if s.strip())
    # fast path using locator has_text
    for sel in selectors:
        try:
            await page.locator(sel, has_text=text).first.wait_for(timeout=timeout_ms)
            return True
        except Exception:
            continue
    # fallback path: normalize both sides
    target = normalize_text(text)
    for sel in selectors:
        try:
            # query a small set of nodes and inspect text
            loc = page.locator(sel)
            n = await loc.count()
            n = min(n, 20)
            for i in range(n):
                s = await loc.nth(i).inner_text()
                if normalize_text(s).find(target) >= 0:
                    return True
        except Exception:
            continue
    return False


async def wait_reply_by_author(page: Page, handle: str, text: str, timeout_ms: int = 6000) -> bool:
    try:
        # Look for an article with an anchor to /{handle} and the reply text
        locator = page.locator("article").filter(
            has=page.locator(f"a[href='/{handle}']"),
            has_text=text,
        )
        await locator.first.wait_for(timeout=timeout_ms)
        return True
    except Exception:
        return False


async def wait_post_on_profile_by_text(page: Page, handle: str, text: str, max_articles: int = 20, timeout_ms: int = 8000) -> bool:
    try:
        # look through first N articles on profile for text
        arts = page.locator("article").filter(has=page.locator(f"a[href='/{handle}']"))
        count = await arts.count()
        count = min(count, max_articles)
        for i in range(count):
            art = arts.nth(i)
            try:
                await art.get_by_text(text, exact=False).wait_for(timeout=timeout_ms)
                return True
            except Exception:
                continue
        return False
    except Exception:
        return False
