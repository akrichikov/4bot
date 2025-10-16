from __future__ import annotations

from .waits import wait_any_visible, click_any_when_ready
from playwright.async_api import Page


MEDIA_EDITOR_DONE = (
    "div[role='button'][data-testid='doneButton']",
    "button[data-testid='doneButton']",
    "div[role='button'][data-testid='headerClose']",
)


async def dismiss_media_editor_if_present(page: Page) -> bool:
    sel = await wait_any_visible(page, MEDIA_EDITOR_DONE, timeout_ms=2000)
    if sel:
        await click_any_when_ready(page, MEDIA_EDITOR_DONE)
        return True
    return False

