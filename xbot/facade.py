from __future__ import annotations

from asyncio import sleep
from typing import Optional

from playwright.async_api import Page

from .browser import Browser
from .config import Config
from .flows.login import login_if_needed
from .flows.media import post_with_media
from .media import validate_files, order_files, cap_files, files_metadata
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
    TWEET_TEXT_SELECTORS,
)
from .utils import jitter, with_retries
from .human import type_text
from .telemetry import JsonLogger
from .artifacts import capture_error
from .ratelimit import RateLimiter
from .results import record_action_result
from .waits import (
    click_when_ready,
    wait_visible,
    click_any_when_ready,
    wait_any_visible,
    wait_toast,
    wait_text_in,
    wait_reply_by_author,
    wait_post_on_profile_by_text,
    parse_status_id,
    extract_status_id_from_profile,
)
from .errors import classify_exception
from .compose import ensure_composer_with_feed
from .vterm_client import VTermClient


class XBot:
    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or Config.from_env()
        self.log = JsonLogger(self.cfg)
        self.rate = RateLimiter(self.cfg.rate_min_s, self.cfg.rate_max_s, self.cfg.rate_enabled)

    @with_retries(3)
    async def post(self, text: str) -> None:
        await self.rate.wait("post")
        async with Browser(self.cfg, label="post") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("post", {"len": len(text)}):
                try:
                    await self._compose_and_submit(page, text)
                    confirmed_toast = await wait_toast(page, TOAST_REGION, timeout_ms=self.cfg.toast_timeout_ms) if 'TOAST_REGION' in globals() else False
                    confirmed_text = False
                    if self.cfg.confirm_content_enabled:
                        confirmed_text = await wait_text_in(page, TWEET_TEXT_SELECTORS, text, timeout_ms=self.cfg.content_confirm_timeout_ms)
                        if not confirmed_text and self.cfg.confirm_post_profile_nav and self.cfg.handle:
                            # Navigate to profile and verify content appears (author-aware)
                            await page.goto(f"{self.cfg.base_url.rstrip('/')}/{self.cfg.handle}", wait_until="domcontentloaded")
                            confirmed_text = await wait_post_on_profile_by_text(page, self.cfg.handle, text, max_articles=25, timeout_ms=self.cfg.content_confirm_timeout_ms)
                    confirm_label = "toast+content" if (confirmed_toast and confirmed_text) else ("content" if confirmed_text else ("toast" if confirmed_toast else "unknown"))
                    meta = {"len": len(text), "confirm": confirm_label}
                    # attempt to capture status id from profile when available
                    status_id = None
                    if self.cfg.confirm_post_profile_nav and self.cfg.handle and confirmed_text:
                        status_id = await extract_status_id_from_profile(page, self.cfg.handle, text, max_articles=25, timeout_ms=4000)
                    # strict gating
                    success = True
                    if self.cfg.confirm_post_strict and not confirmed_text:
                        success = False
                    record_action_result(
                        "post",
                        success,
                        self.cfg,
                        {**meta, **({"status_id": status_id} if status_id else {})},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "post")  # type: ignore[arg-type]
                    self.log.artifact("post", paths)
                    record_action_result(
                        "post",
                        False,
                        self.cfg,
                        {"len": len(text), "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
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
                    confirmed = await wait_toast(page, TOAST_REGION, timeout_ms=self.cfg.toast_timeout_ms) if 'TOAST_REGION' in globals() else False
                    if self.cfg.confirm_content_enabled and not confirmed:
                        # try to locate our reply text in thread; prefer author match if handle known
                        if self.cfg.handle:
                            confirmed = await wait_reply_by_author(page, self.cfg.handle, text, timeout_ms=self.cfg.content_confirm_timeout_ms)
                        if not confirmed:
                            confirmed = await wait_text_in(page, TWEET_TEXT_SELECTORS, text, timeout_ms=self.cfg.content_confirm_timeout_ms)
                    status_id = None
                    if self.cfg.handle and confirmed:
                        # attempt author-aware status id extraction from thread
                        status_id = await extract_reply_status_id_from_thread(page, self.cfg.handle, text, timeout_ms=self.cfg.content_confirm_timeout_ms)
                        if not status_id:
                            # fallback to /with_replies timeline
                            status_id = await extract_reply_status_id_from_with_replies(page, self.cfg.base_url, self.cfg.handle, text, max_articles=25, timeout_ms=self.cfg.content_confirm_timeout_ms)
                    success = True
                    if self.cfg.confirm_reply_strict and not confirmed:
                        success = False
                    record_action_result(
                        "reply",
                        success,
                        self.cfg,
                        {"url": url, "len": len(text), "confirm": ("toast" if confirmed else "unknown"), **({"status_id": status_id} if status_id else {})},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "reply")  # type: ignore[arg-type]
                    self.log.artifact("reply", paths)
                    record_action_result(
                        "reply",
                        False,
                        self.cfg,
                        {"url": url, "len": len(text), "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
    async def like(self, url: str) -> None:
        await self.rate.wait("like")
        async with Browser(self.cfg, label="like") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("like", {"url": url}):
                try:
                    target_url = _to_status(self.cfg, url)
                    target_sid = parse_status_id(target_url)
                    await page.goto(target_url, wait_until="domcontentloaded")
                    # idempotent: if already liked, skip
                    if await page.locator(UNLIKE_BUTTON).first.count() == 0:
                        await click_when_ready(page, LIKE_BUTTON)
                        await wait_visible(page, UNLIKE_BUTTON, timeout_ms=self.cfg.wait_timeout_ms)
                    await sleep(0.5)
                    verified = True
                    if target_sid:
                        verified = await verify_status_context(page, target_sid, timeout_ms=self.cfg.wait_timeout_ms)
                        if not verified:
                            await page.goto(f"{self.cfg.base_url.rstrip('/')}/i/web/status/{target_sid}", wait_until="domcontentloaded")
                            verified = await verify_status_context(page, target_sid, timeout_ms=self.cfg.wait_timeout_ms)
                    record_action_result(
                        "like",
                        True,
                        self.cfg,
                        {"url": url, **({"status_id": target_sid, "verified": verified} if target_sid else {})},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "like")  # type: ignore[arg-type]
                    self.log.artifact("like", paths)
                    record_action_result(
                        "like",
                        False,
                        self.cfg,
                        {"url": url, "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
    async def retweet(self, url: str) -> None:
        await self.rate.wait("retweet")
        async with Browser(self.cfg, label="retweet") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            async with self.log.action("retweet", {"url": url}):
                try:
                    target_url = _to_status(self.cfg, url)
                    target_sid = parse_status_id(target_url)
                    await page.goto(target_url, wait_until="domcontentloaded")
                    # idempotent: if already retweeted, skip
                    if await page.locator(UNRETWEET_BUTTON).first.count() == 0:
                        await click_when_ready(page, RETWEET_BUTTON)
                        await click_when_ready(page, RETWEET_CONFIRM)
                        await wait_visible(page, UNRETWEET_BUTTON, timeout_ms=self.cfg.wait_timeout_ms)
                    await sleep(0.5)
                    verified = True
                    if target_sid:
                        verified = await verify_status_context(page, target_sid, timeout_ms=self.cfg.wait_timeout_ms)
                        if not verified:
                            await page.goto(f"{self.cfg.base_url.rstrip('/')}/i/web/status/{target_sid}", wait_until="domcontentloaded")
                            verified = await verify_status_context(page, target_sid, timeout_ms=self.cfg.wait_timeout_ms)
                    record_action_result(
                        "retweet",
                        True,
                        self.cfg,
                        {"url": url, **({"status_id": target_sid, "verified": verified} if target_sid else {})},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "retweet")  # type: ignore[arg-type]
                    self.log.artifact("retweet", paths)
                    record_action_result(
                        "retweet",
                        False,
                        self.cfg,
                        {"url": url, "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    # -------------------------- VTERM ACTIONS --------------------------
    async def vterm_run(self, cmd: str, timeout: float = 10.0) -> dict:
        client = self._vterm_client()
        try:
            if client.mode == "http":
                res = await client.run_http(cmd, timeout=timeout)
            else:
                import asyncio
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, client.run_unix, cmd, timeout)
            record_action_result("vterm_run", True, self.cfg, {"cmd": cmd, "exit_code": res.get("exit_code")})
            return res
        except Exception as e:
            record_action_result("vterm_run", False, self.cfg, {"cmd": cmd, "error": str(e)})
            raise

    async def vterm_write(self, text: str) -> dict:
        client = self._vterm_client()
        try:
            if client.mode == "http":
                res = await client.write_http(text)
            else:
                import asyncio
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, client.write_unix, text)
            record_action_result("vterm_write", True, self.cfg, {"bytes": len(text)})
            return res
        except Exception as e:
            record_action_result("vterm_write", False, self.cfg, {"error": str(e)})
            raise

    async def vterm_read(self, timeout: float = 0.2) -> dict:
        client = self._vterm_client()
        try:
            if client.mode == "http":
                res = await client.read_http(timeout)
            else:
                import asyncio
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, client.read_unix, timeout)
            record_action_result("vterm_read", True, self.cfg, {"lines": len(res.get("lines", []))})
            return res
        except Exception as e:
            record_action_result("vterm_read", False, self.cfg, {"error": str(e)})
            raise

    def _vterm_client(self) -> VTermClient:
        if self.cfg.vterm_mode == "http":
            base = self.cfg.vterm_http_base or "http://127.0.0.1:9876"
            return VTermClient(mode="http", base=base, token=self.cfg.vterm_token)
        return VTermClient(mode="unix", socket_path=str(self.cfg.vterm_socket))

    async def _compose_and_submit(self, page: Page, text: str) -> None:
        await page.goto(self.cfg.base_url + COMPOSE_URL, wait_until="domcontentloaded")
        # Ensure composer visible; fall back to feed composer
        await ensure_composer_with_feed(page, self.cfg, timeout_ms=self.cfg.wait_timeout_ms)
        sel = await wait_any_visible(page, COMPOSE_TEXTBOX)
        target = sel or (COMPOSE_TEXTBOX[0] if isinstance(COMPOSE_TEXTBOX, tuple) else COMPOSE_TEXTBOX)  # type: ignore[arg-type]
        if self.cfg.humanize:
            await type_text(page.locator(target).first, text, self.cfg.type_min_ms, self.cfg.type_max_ms)
        else:
            await page.locator(target).first.fill(text)
        await click_any_when_ready(page, COMPOSE_SUBMIT)
        await sleep(1.0)

    async def post_media(self, text: str, files: list[str]) -> None:
        await self.rate.wait("post_media")
        async with Browser(self.cfg, label="post_media") as b:
            page = b.page
            await login_if_needed(page, self.cfg)
            from pathlib import Path

            paths = order_files([Path(p) for p in files])
            # apply platform caps
            capped_files, cap_meta = cap_files(paths)
            check = validate_files(self.cfg, capped_files)
            meta = {
                "len": len(text),
                "files": len(paths),
                "accepted": len(check.files),
                "reasons": check.reasons,
                "cap": cap_meta,
                "files_meta": files_metadata(check.files),
            }
            async with self.log.action("post_media", meta):
                try:
                    if not check.ok:
                        raise ValueError(f"media_validation_failed: {check.reasons}")
                    previews = await post_with_media(page, text, check.files)
                    meta["previews"] = previews
                    preview_ok = previews >= len(check.files)
                    # success gating
                    success = True
                    if cap_meta.get("capped") and self.cfg.media_cap_enforce and not self.cfg.media_cap_warn_only:
                        success = False
                    if self.cfg.media_preview_enforce and not preview_ok:
                        success = self.cfg.media_preview_warn_only is False
                    record_action_result(
                        "post_media",
                        success,
                        self.cfg,
                        {**meta, "preview_ok": preview_ok},
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                except Exception as e:
                    paths_art = await capture_error(page, b._ctx, self.cfg, "post_media")  # type: ignore[arg-type]
                    self.log.artifact("post_media", paths_art)
                    record_action_result(
                        "post_media",
                        False,
                        self.cfg,
                        {**meta, "error": classify_exception(e)},
                        artifacts=paths_art,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
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
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "follow")  # type: ignore[arg-type]
                    self.log.artifact("follow", paths)
                    record_action_result(
                        "follow",
                        False,
                        self.cfg,
                        {"profile": profile_url, "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
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
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "unfollow")  # type: ignore[arg-type]
                    self.log.artifact("unfollow", paths)
                    record_action_result(
                        "unfollow",
                        False,
                        self.cfg,
                        {"profile": profile_url, "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise

    @with_retries(3)
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
                except Exception as e:
                    paths = await capture_error(page, b._ctx, self.cfg, "dm")  # type: ignore[arg-type]
                    self.log.artifact("dm", paths)
                    record_action_result(
                        "dm",
                        False,
                        self.cfg,
                        {"profile": profile_url, "len": len(text), "error": classify_exception(e)},
                        artifacts=paths,
                        trace_path=str(b.trace_path) if b.trace_path else None,
                        har_path=str(b.har_path) if b.har_path else None,
                    )
                    raise
                finally:
                    await jitter(self.cfg.jitter_min_ms, self.cfg.jitter_max_ms)
                confirmed = await wait_toast(page, TOAST_REGION, timeout_ms=4000) if 'TOAST_REGION' in globals() else False
                record_action_result(
                    "dm",
                    True,
                    self.cfg,
                    {"profile": profile_url, "len": len(text), "confirm": "toast" if confirmed else "unknown"},
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
