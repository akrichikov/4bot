from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import BrowserContext


async def apply_storage_state(context: BrowserContext, storage_file: Path) -> None:
    if not storage_file.exists():
        return
    data = json.loads(storage_file.read_text())
    cookies: List[Dict[str, Any]] = data.get("cookies", [])
    origins: List[Dict[str, Any]] = data.get("origins", [])

    if cookies:
        await context.add_cookies(cookies)  # type: ignore[arg-type]

    if origins:
        page = await context.new_page()
        for origin in origins:
            origin_url = origin.get("origin")
            if not origin_url:
                continue
            await page.goto(origin_url)
            for item in origin.get("localStorage", []):
                name = item.get("name")
                value = item.get("value")
                if name is None or value is None:
                    continue
                await page.evaluate(
                    "([n, v]) => localStorage.setItem(n, v)", [name, value]
                )
        await page.close()


async def export_storage_state(context: BrowserContext, storage_file: Path) -> None:
    storage_file.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(storage_file))  # type: ignore[arg-type]
