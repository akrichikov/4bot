from __future__ import annotations

from asyncio import sleep
from typing import Optional

from playwright.async_api import Page

from .browser import Browser
from .config import Config
from .flows.login import login_if_needed
from .flows.media import post_with_media
from .media import validate_files, order_files
from .selectors import (
    COMPOSE_SUBMIT,
    COMPOSE_TEXTBOX,
    COMPOSE_URL,
    FOLLOW_BUTTON,
    LIKE_BUTTON,
    MESSAGE_BUTTON,
    REPLY_BUTTON,
    REPLY_SUBMIT,
    REPLY_TEXTBOX,
    RETWEET_BUTTON,
    RETWEET_CONFIRM,
    UNFOLLOW_BUTTON,
    UNLIKE_BUTTON,
    UNRETWEET_BUTTON,
)
from .utils import jitter, with_retries
from .human import type_text
from .telemetry import JsonLogger
from .artifacts import capture_error
from .ratelimit import RateLimiter
from .results import record_action_result
from .waits import click_when_ready, wait_visible, click_any_when_ready, wait_any_visible


class XBot:
    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or Config.from_env()
        self.log = JsonLogger(self.cfg)
        self.rate = RateLimiter(self.cfg.rate_min_s, self.cfg.rate_max_s, self.cfg.rate_enabled)

    @with_retries(attempts=3)
    async def post(self, text: str) -> None:
        await self.rate.wait("post")
        async with Browser(self.cfg, label="post") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("post", {"len": len(text)}):
                try:
                    await self._compose_and_submit(page, text)
                    record_action_result(
                        "post",
                        True,
                        self.cfg,
                        {"len": len(text)},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "post")  # type: ignore[arg-type]
                    self.log.artifact("post", paths)
                    record_action_result(
                        "post",
                        False,
                        self.cfg,
                        {"len": len(text)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def reply(self, url: str, text: str) -> None:
        await self.rate.wait("reply")
        async with Browser(self.cfg, label="reply") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("reply", {"url": url, "len": len(text)}):
                await page.goto(_to_status(self.cfg, url), wait_until="domcontentloaded")
                await click_when_ready(page, REPLY_BUTTON)
                try:
                    if self.cfg.humanize:
                        await type_text(page.locator(REPLY_TEXTBOX).first, text, self.cfg.type_min_ms, self.cfg.type_max_ms)
                    else:
                        await page.locator(REPLY_TEXTBOX).first.fill(text)
                    await click_any_when_ready(page, REPLY_SUBMIT)
                    await sleep(1.0)
                    record_action_result(
                        "reply",
                        True,
                        self.cfg,
                        {"url": url, "len": len(text)},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "reply")  # type: ignore[arg-type]
                    self.log.artifact("reply", paths)
                    record_action_result(
                        "reply",
                        False,
                        self.cfg,
                        {"url": url, "len": len(text)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def like(self, url: str) -> None:
        await self.rate.wait("like")
        async with Browser(self.cfg, label="like") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("like", {"url": url}):
                try:
                    await page.goto(_to_status(self.cfg, url), wait_until="domcontentloaded")
                    # idempotent: if already liked, skip
                    if await page.locator(UNLIKE_BUTTON).first.count() == 0:
                        await click_when_ready(page, LIKE_BUTTON)
                    await sleep(0.5)
                    record_action_result(
                        "like",
                        True,
                        self.cfg,
                        {"url": url},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "like")  # type: ignore[arg-type]
                    self.log.artifact("like", paths)
                    record_action_result(
                        "like",
                        False,
                        self.cfg,
                        {"url": url},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def retweet(self, url: str) -> None:
        await self.rate.wait("retweet")
        async with Browser(self.cfg, label="retweet") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("retweet", {"url": url}):
                try:
                    await page.goto(_to_status(self.cfg, url), wait_until="domcontentloaded")
                    # idempotent: if already retweeted, skip
                    if await page.locator(UNRETWEET_BUTTON).first.count() == 0:
                        await click_when_ready(page, RETWEET_BUTTON)
                        await click_when_ready(page, RETWEET_CONFIRM)
                    await sleep(0.5)
                    record_action_result(
                        "retweet",
                        True,
                        self.cfg,
                        {"url": url},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "retweet")  # type: ignore[arg-type]
                    self.log.artifact("retweet", paths)
                    record_action_result(
                        "retweet",
                        False,
                        self.cfg,
                        {"url": url},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    async def _compose_and_submit(self, page: Page, text: str) -> None:
        await page.goto(self.cfg.base_url + COMPOSE_URL, wait_until="domcontentloaded")
        if self.cfg.humanize:
            await type_text(page.locator(COMPOSE_TEXTBOX).first, text, self.cfg.type_min_ms, self.cfg.type_max_ms)
        else:
            await page.locator(COMPOSE_TEXTBOX).first.fill(text)
        await page.locator(COMPOSE_SUBMIT).first.click()
        await sleep(1.0)

    async def post_media(self, text: str, files: list[str]) -> None:
        await self.rate.wait("post_media")
        async with Browser(self.cfg, label="post_media") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            from pathlib import Path

            paths = order_files([Path(p) for p in files])
            check = validate_files(self.cfg, paths)
            meta = {"len": len(text), "files": len(paths), "accepted": len(check.files), "reasons": check.reasons}
            async with self.log.action("post_media", meta):
                try:
                    if not check.ok:
                        raise ValueError(f"media_validation_failed: {check.reasons}")
                    await post_with_media(page, text, check.files)
                    record_action_result(
                        "post_media",
                        True,
                        self.cfg,
                        meta,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths_art = await capture_error(page, b._ctx, self.cfg, "post_media")  # type: ignore[arg-type]
                    self.log.artifact("post_media", paths_art)
                    record_action_result(
                        "post_media",
                        False,
                        self.cfg,
                        meta,
                        artifacts=paths_art,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def follow(self, profile_url: str) -> None:
        await self.rate.wait("follow")
        async with Browser(self.cfg, label="follow") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("follow", {"profile": profile_url}):
                try:
                    await page.goto(_to_profile(self.cfg, profile_url), wait_until="domcontentloaded")
                    await click_when_ready(page, FOLLOW_BUTTON)
                    await jitter(self.cfg.jitter_min_ms, self.cfg.jitter_max_ms)
                    record_action_result(
                        "follow",
                        True,
                        self.cfg,
                        {"profile": profile_url},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "follow")  # type: ignore[arg-type]
                    self.log.artifact("follow", paths)
                    record_action_result(
                        "follow",
                        False,
                        self.cfg,
                        {"profile": profile_url},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def unfollow(self, profile_url: str) -> None:
        await self.rate.wait("unfollow")
        async with Browser(self.cfg, label="unfollow") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("unfollow", {"profile": profile_url}):
                try:
                    await page.goto(_to_profile(self.cfg, profile_url), wait_until="domcontentloaded")
                    await click_when_ready(page, UNFOLLOW_BUTTON)
                    await jitter(self.cfg.jitter_min_ms, self.cfg.jitter_max_ms)
                    record_action_result(
                        "unfollow",
                        True,
                        self.cfg,
                        {"profile": profile_url},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "unfollow")  # type: ignore[arg-type]
                    self.log.artifact("unfollow", paths)
                    record_action_result(
                        "unfollow",
                        False,
                        self.cfg,
                        {"profile": profile_url},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(attempts=3)
    async def dm(self, profile_url: str, text: str) -> None:
        await self.rate.wait("dm")
        async with Browser(self.cfg, label="dm") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("dm", {"profile": profile_url, "len": len(text)}):
                await page.goto(_to_profile(self.cfg, profile_url), wait_until="domcontentloaded")
                await click_when_ready(page, MESSAGE_BUTTON)
                try:
                    sel = await wait_any_visible(page, (
                        "div[role='textbox'][data-testid='dmComposerTextInput']",
                        "textarea[data-testid='dmComposerTextInput']",
                    ))
                    target = sel or "div[role='textbox'][data-testid='dmComposerTextInput']"
                    if self.cfg.humanize:
                        await type_text(page.locator(target).first, text, self.cfg.type_min_ms, self.cfg.type_max_ms)
                    else:
                        await page.locator(target).first.fill(text)
                    await click_any_when_ready(page, (
                        "div[role='button'][data-testid='dmComposerSendButton']",
                        "button[data-testid='dmComposerSendButton']",
                    ))
                except Exception:
                    paths = await capture_error(page, b._ctx, self.cfg, "dm")  # type: ignore[arg-type]
                    self.log.artifact("dm", paths)
                    record_action_result(
                        "dm",
                        False,
                        self.cfg,
                        {"profile": profile_url, "len": len(text)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise
                finally:
                    await jitter(self.cfg.jitter_min_ms, self.cfg.jitter_max_ms)
                record_action_result(
                    "dm",
                    True,
                    self.cfg,
                    {"profile": profile_url, "len": len(text)},
                    trace_path=str(b.trace_path) if b.trace_path else None,
                    har_path=str(b.har_path) if b.har_path else None,
                )


def _to_status(cfg: Config, candidate: str) -> str:
    u = candidate.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.isdigit():
        return f"{cfg.base_url.rstrip('/')}/i/web/status/{u}"
    if u.startswith("/"):
        return f"{cfg.base_url.rstrip('/')}{u}"
    return f"{cfg.base_url.rstrip('/')}/{u}"


def _to_profile(cfg: Config, handle_or_url: str) -> str:
    u = handle_or_url.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("@"):
        u = u[1:]
    return f"{cfg.base_url.rstrip('/')}/{u}"
