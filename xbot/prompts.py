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


async def click_button_by_text(page: Page, texts: tuple[str, ...], timeout_ms: int = 2000) -> bool:
    for t in texts:
        try:
            btn = page.get_by_role("button", name=t)
            if await btn.count() > 0:
                await btn.first.click()
                return True
        except Exception:
            pass
        try:
            loc = page.locator("button, div[role='button']", has_text=t)
            if await loc.count() > 0:
                await loc.first.click()
                return True
        except Exception:
            pass
    return False


async def dismiss_media_editors(page: Page) -> bool:
    changed = False
    # Try known data-testids
    if await dismiss_media_editor_if_present(page):
        changed = True
    # Try common text buttons for video/GIF editors
    if await click_button_by_text(page, ("Done", "Apply", "Save", "Use", "OK", "Next")):
        changed = True
    return changed
