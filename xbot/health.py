from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from playwright.async_api import TimeoutError as PwTimeoutError

from .browser import Browser
from .config import Config
from .flows.login import is_logged_in, login_if_needed
from .selectors import (
    COMPOSE_SUBMIT,
    COMPOSE_TEXTBOX,
    COMPOSE_URL,
    FOLLOW_BUTTON,
    LIKE_BUTTON,
    MESSAGE_BUTTON,
    REPLY_BUTTON,
    RETWEET_BUTTON,
    UNFOLLOW_BUTTON,
)
from .facade import _to_profile, _to_status
from .selectors import UNLIKE_BUTTON, UNRETWEET_BUTTON


@dataclass
class CheckResult:
    name: str
    passed: bool
    skipped: bool = False
    detail: str = ""


@dataclass
class HealthReport:
    results: List[CheckResult]

    @property
    def all_passed(self) -> bool:
        return all(r.passed or r.skipped for r in self.results)


async def run_selector_health(cfg: Config, tweet_url: Optional[str] = None, profile: Optional[str] = None) -> HealthReport:
    results: List[CheckResult] = []
    async with Browser(cfg, label="health_selectors") as b:
        page = b.page
        try:
            await login_if_needed(page, cfg)
            results.append(CheckResult("login", await is_logged_in(page)))
        except Exception as e:
            results.append(CheckResult("login", False, detail=str(e)))

        # Compose
        try:
            await page.goto(cfg.base_url + COMPOSE_URL, wait_until="domcontentloaded")
            ok = await page.locator(COMPOSE_TEXTBOX).first.count() > 0 and await page.locator(COMPOSE_SUBMIT).first.count() > 0
            results.append(CheckResult("compose", ok))
        except Exception as e:
            results.append(CheckResult("compose", False, detail=str(e)))

        # Tweet actions
        if tweet_url:
            try:
                await page.goto(_to_status(cfg, tweet_url), wait_until="domcontentloaded")
                ok = (
                    await page.locator(REPLY_BUTTON).first.count() > 0
                    and await page.locator(LIKE_BUTTON).first.count() > 0
                    and await page.locator(RETWEET_BUTTON).first.count() > 0
                )
                results.append(CheckResult("tweet_actions", ok))
            except Exception as e:
                results.append(CheckResult("tweet_actions", False, detail=str(e)))
        else:
            results.append(CheckResult("tweet_actions", False, skipped=True, detail="No tweet_url provided"))

        # Profile actions
        if profile:
            try:
                await page.goto(_to_profile(cfg, profile), wait_until="domcontentloaded")
                # Either follow or unfollow button may be present depending on state; message optional
                has_follow = await page.locator(FOLLOW_BUTTON).first.count() > 0
                has_unfollow = await page.locator(UNFOLLOW_BUTTON).first.count() > 0
                has_msg = await page.locator(MESSAGE_BUTTON).first.count() > 0
                results.append(CheckResult("profile_actions", (has_follow or has_unfollow or has_msg)))
            except Exception as e:
                results.append(CheckResult("profile_actions", False, detail=str(e)))
        else:
            results.append(CheckResult("profile_actions", False, skipped=True, detail="No profile provided"))

    return HealthReport(results)


async def tweet_state(cfg: Config, url: str) -> Dict[str, bool]:
    async with Browser(cfg, label="health_tweet_state") as b:
        page = b.page
        await page.goto(_to_status(cfg, url), wait_until="domcontentloaded")
        liked = (await page.locator(UNLIKE_BUTTON).first.count()) > 0
        retweeted = (await page.locator(UNRETWEET_BUTTON).first.count()) > 0
        return {"liked": liked, "retweeted": retweeted}


async def compose_health(cfg: Config) -> Dict[str, bool]:
    async with Browser(cfg, label="health_compose") as b:
        page = b.page
        await page.goto(cfg.base_url + COMPOSE_URL, wait_until="domcontentloaded")
        has_box = (await page.locator(COMPOSE_TEXTBOX).first.count()) > 0
        has_submit = (await page.locator(COMPOSE_SUBMIT).first.count()) > 0
        return {"compose_textbox": has_box, "compose_submit": has_submit}
