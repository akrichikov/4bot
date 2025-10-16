from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from playwright.async_api import BrowserContext, Page

from .config import Config


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


async def capture_error(page: Page, ctx: BrowserContext, cfg: Config, label: str) -> Dict[str, str]:
    t = _ts()
    screens = Path("artifacts/screens"); screens.mkdir(parents=True, exist_ok=True)
    htmls = Path("artifacts/html"); htmls.mkdir(parents=True, exist_ok=True)

    screen_path = screens / f"{label}_{t}.png"
    html_path = htmls / f"{label}_{t}.html"

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

