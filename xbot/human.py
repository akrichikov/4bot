from __future__ import annotations

import random
from typing import Iterable

from playwright.async_api import Locator, Page


async def type_text(locator: Locator, text: str, min_ms: int = 20, max_ms: int = 60) -> None:
    delay = random.randint(min_ms, max_ms)
    await locator.type(text, delay=delay)


async def quick_read(page: Page, min_px: int = 200, max_px: int = 800) -> None:
    delta = random.randint(min_px, max_px)
    await page.mouse.wheel(0, delta)


async def hover_jitter(locator: Locator) -> None:
    await locator.hover()

