from __future__ import annotations

from datetime import datetime
from typing import Dict

from playwright.async_api import BrowserContext, Page

from .config import Config
from .utils import timestamped


async def capture_error(page: Page, ctx: BrowserContext, cfg: Config, label: str) -> Dict[str, str]:
    screen_path = timestamped(cfg, "screens", label, ".png")
    html_path = timestamped(cfg, "html", label, ".html")

    try:
        await page.screenshot(path=str(screen_path), full_page=True)
    except Exception:
        pass
    try:
        html = await page.content()
        html_path.write_text(html, encoding="utf-8")
    except Exception:
        pass

    return {"screenshot": str(screen_path), "html": str(html_path)}
