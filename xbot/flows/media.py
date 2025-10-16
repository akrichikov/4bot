from __future__ import annotations

from pathlib import Path
from typing import Iterable

from playwright.async_api import Page

from ..selectors import COMPOSE_SUBMIT, COMPOSE_TEXTBOX, COMPOSE_URL
from ..waits import click_any_when_ready, wait_count_at_least
from ..prompts import dismiss_media_editor_if_present

MEDIA_INPUT = "input[type='file'][accept*='image'], input[type='file'][accept*='video'], input[type='file'][data-testid='fileInput']"
MEDIA_PREVIEW = "div[data-testid='mediaAttachment'], div[data-testid='attachments']"


async def post_with_media(page: Page, text: str, files: Iterable[Path]) -> None:
    await page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    box = page.locator(COMPOSE_TEXTBOX).first
    if await box.count() == 0:
        await page.click("body")
    await page.locator(COMPOSE_TEXTBOX).first.fill(text)
    file_paths = [str(Path(f)) for f in files]
    if file_paths:
        await page.locator(MEDIA_INPUT).first.set_input_files(file_paths)
        # wait for at least one preview; try to match count but fall back to 1
        count = len(file_paths)
        ok = await wait_count_at_least(page, MEDIA_PREVIEW, max(1, min(count, 4)), timeout_ms=20000)
        if not ok:
            await page.locator(MEDIA_PREVIEW).first.wait_for(timeout=10000)
        # if editor modal appears, dismiss with Done/Close
        await dismiss_media_editor_if_present(page)
    await click_any_when_ready(page, COMPOSE_SUBMIT)
