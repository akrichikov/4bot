from __future__ import annotations

from pathlib import Path
from typing import Iterable

from playwright.async_api import Page

from ..selectors import COMPOSE_SUBMIT, COMPOSE_TEXTBOX, COMPOSE_URL
from ..waits import click_any_when_ready, wait_count_at_least
from ..prompts import dismiss_media_editor_if_present, dismiss_media_editors

MEDIA_INPUT = "input[type='file'][accept*='image'], input[type='file'][accept*='video'], input[type='file'][data-testid='fileInput']"
MEDIA_PREVIEW = "div[data-testid='mediaAttachment'], div[data-testid='attachments']"


async def post_with_media(page: Page, text: str, files: Iterable[Path]) -> int:
    await page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    from ..waits import wait_any_visible
    sel = await wait_any_visible(page, COMPOSE_TEXTBOX)
    if not sel:
        await page.click("body")
    target = sel or (COMPOSE_TEXTBOX[0] if isinstance(COMPOSE_TEXTBOX, tuple) else COMPOSE_TEXTBOX)
    await page.locator(target).first.fill(text)
    file_paths = [str(Path(f)) for f in files]
    previews = 0
    if file_paths:
        await page.locator(MEDIA_INPUT).first.set_input_files(file_paths)
        # wait for at least one preview; try to match count but fall back to 1
        count = len(file_paths)
        ok = await wait_count_at_least(page, MEDIA_PREVIEW, max(1, min(count, 4)), timeout_ms=getattr(page.context, 'cfg_long_wait_timeout_ms', None) or 20000)
        if not ok:
            await page.locator(MEDIA_PREVIEW).first.wait_for(timeout=10000)
        # if editor modal appears (image/video/GIF), dismiss with known or text-based buttons
        await dismiss_media_editors(page)
        try:
            previews = await page.locator(MEDIA_PREVIEW).count()
        except Exception:
            previews = 0
    await click_any_when_ready(page, COMPOSE_SUBMIT)
    return previews
