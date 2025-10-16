from __future__ import annotations

from .waits import wait_any_visible, click_any_when_ready
from .utils import jitter
from .selectors import COMPOSE_TEXTBOX, COMPOSE_OPENERS, FEED_COMPOSER_HITBOX
from .config import Config
from playwright.async_api import Page


async def ensure_composer(page: Page, timeout_ms: int = 5000, base_url: str | None = None) -> bool:
    sel = await wait_any_visible(page, COMPOSE_TEXTBOX, timeout_ms=timeout_ms)
    if sel:
        return True
    # try openers
    try:
        await click_any_when_ready(page, COMPOSE_OPENERS, timeout_ms=timeout_ms)
    except Exception:
        pass
    sel2 = await wait_any_visible(page, COMPOSE_TEXTBOX, timeout_ms=timeout_ms)
    return bool(sel2)


async def ensure_composer_with_feed(page: Page, cfg: Config, timeout_ms: int | None = None) -> bool:
    # attempt modal first, then fallback to feed; retry using cfg.action_retries
    timeout = timeout_ms or cfg.wait_timeout_ms
    for attempt in range(max(1, cfg.action_retries)):
        if await ensure_composer(page, timeout_ms=timeout_ms):
            return True
        try:
            await page.goto(cfg.base_url, wait_until="domcontentloaded")
            await click_any_when_ready(page, FEED_COMPOSER_HITBOX, timeout_ms=timeout)
        except Exception:
            try:
                await click_any_when_ready(page, COMPOSE_TEXTBOX, timeout_ms=timeout)
            except Exception:
                pass
        if await wait_any_visible(page, COMPOSE_TEXTBOX, timeout_ms=timeout):
            return True
        await jitter(cfg.action_retry_jitter_min_ms, cfg.action_retry_jitter_max_ms)
    return False
