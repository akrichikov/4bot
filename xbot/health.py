from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

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
from .browser import Browser
import json
import re
from .selectors import UNLIKE_BUTTON, UNRETWEET_BUTTON
from .cookies import load_cookies_best_effort
from .rabbitmq_manager import RabbitMQManager
import aiohttp
from time import perf_counter as _perf


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


async def selectors_snapshot(cfg: Config, tweet_url: Optional[str] = None, profile: Optional[str] = None) -> Dict[str, Any]:
    snap: Dict[str, Any] = {"compose": {}, "tweet": {}, "profile": {}}
    async with Browser(cfg, label="health_snapshot") as b:
        page = b.page
        # compose page
        try:
            await page.goto(cfg.base_url + COMPOSE_URL, wait_until="domcontentloaded")
            tcount = await page.locator(COMPOSE_TEXTBOX).count()
            scount = await page.locator(COMPOSE_SUBMIT).count()
            snap["compose"].update({"textbox": tcount > 0, "textbox_count": tcount, "submit": scount > 0, "submit_count": scount})
        except Exception as e:
            snap["compose"]["error"] = str(e)

        # tweet page
        if tweet_url:
            try:
                await page.goto(_to_status(cfg, tweet_url), wait_until="domcontentloaded")
                rcount = await page.locator(REPLY_BUTTON).count()
                lcount = await page.locator(LIKE_BUTTON).count()
                rtcount = await page.locator(RETWEET_BUTTON).count()
                snap["tweet"].update({"reply": rcount > 0, "reply_count": rcount, "like": lcount > 0, "like_count": lcount, "retweet": rtcount > 0, "retweet_count": rtcount})
                snap["tweet"]["url"] = _to_status(cfg, tweet_url)
            except Exception as e:
                snap["tweet"]["error"] = str(e)
        else:
            snap["tweet"]["skipped"] = True

        # profile page
        if profile:
            try:
                await page.goto(_to_profile(cfg, profile), wait_until="domcontentloaded")
                fcount = await page.locator(FOLLOW_BUTTON).count()
                ufcount = await page.locator(UNFOLLOW_BUTTON).count()
                mcount = await page.locator(MESSAGE_BUTTON).count()
                snap["profile"].update({"follow": fcount > 0, "follow_count": fcount, "unfollow": ufcount > 0, "unfollow_count": ufcount, "message": mcount > 0, "message_count": mcount, "url": _to_profile(cfg, profile)})
            except Exception as e:
                snap["profile"]["error"] = str(e)
        else:
            snap["profile"]["skipped"] = True

    # derived pass/fail booleans
    snap["ok_compose"] = bool(snap["compose"].get("textbox") and snap["compose"].get("submit"))
    if not snap["tweet"].get("skipped"):
        snap["ok_tweet"] = bool(snap["tweet"].get("reply") and snap["tweet"].get("like") and snap["tweet"].get("retweet"))
    else:
        snap["ok_tweet"] = None
    if not snap["profile"].get("skipped"):
        snap["ok_profile"] = bool(snap["profile"].get("follow") or snap["profile"].get("unfollow") or snap["profile"].get("message"))
    else:
        snap["ok_profile"] = None
    return snap


def evaluate_snapshot(snap: Dict[str, Any], require_compose: bool, require_tweet: bool, require_profile: bool) -> bool:
    ok = True
    if require_compose:
        ok = ok and bool(snap.get("ok_compose"))
    if require_tweet:
        ok = ok and bool(snap.get("ok_tweet"))
    if require_profile:
        ok = ok and bool(snap.get("ok_profile"))
    return ok


def drift_hints(snap: Dict[str, Any]) -> List[str]:
    hints: List[str] = []
    if not snap.get("ok_compose"):
        c = snap.get("compose", {})
        if not c.get("textbox"):
            hints.append("Compose textbox not found. Consider updating COMPOSE_TEXTBOX selectors.")
        if not c.get("submit"):
            hints.append("Compose submit button not found. Consider updating COMPOSE_SUBMIT selectors.")
    if snap.get("ok_tweet") is False:
        t = snap.get("tweet", {})
        if not t.get("reply"):
            hints.append("Reply button not found. Update REPLY_BUTTON selectors.")
        if not t.get("like"):
            hints.append("Like button not found. Update LIKE_BUTTON selectors.")
        if not t.get("retweet"):
            hints.append("Retweet button not found. Update RETWEET_BUTTON selectors.")
    if snap.get("ok_profile") is False:
        p = snap.get("profile", {})
        if not (p.get("follow") or p.get("unfollow")):
            hints.append("Follow/Unfollow button not found. Update FOLLOW_BUTTON/UNFOLLOW_BUTTON selectors.")
        if not p.get("message"):
            hints.append("Message button not found. Update MESSAGE_BUTTON selectors.")
    return hints


async def proxy_check(cfg: Config, url: str = "https://api.ipify.org?format=json") -> Dict[str, Any]:
    async with Browser(cfg, label="health_proxy") as b:
        page = b.page
        await page.goto(url, wait_until="domcontentloaded")
        body = (await page.text_content("body")) or ""
        ua = await page.evaluate("() => navigator.userAgent")
        ip = None
        headers = None
        try:
            data = json.loads(body)
            ip = data.get("ip") or data.get("origin")
            headers = data.get("headers")
        except Exception:
            m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", body)
            if m:
                ip = m.group(1)
        return {"url": url, "ip": ip, "headers": headers, "userAgent": ua, "raw": body[:1000]}


async def system_health(cfg: Config, vterm_http_base: str | None = None) -> Dict[str, Any]:
    report: Dict[str, Any] = {"cookies": {}, "storage": {}, "vterm_http": {}, "rabbitmq": {}}

    # Cookies
    cookies = load_cookies_best_effort(profile=cfg.profile_name)
    key_names = {"auth_token", "ct0", "kdt", "att"}
    present = {c.get("name") for c in cookies if isinstance(c, dict)}
    report["cookies"] = {
        "count": len(cookies),
        "keys_present": sorted(list(key_names & present)),
    }

    # Storage
    st = {"path": str(cfg.storage_state), "exists": False, "cookie_count": 0}
    try:
        st["exists"] = cfg.storage_state.exists()
        if st["exists"]:
            data = json.loads(cfg.storage_state.read_text())
            st["cookie_count"] = len(data.get("cookies", []))
    except Exception as e:
        st["error"] = str(e)
    report["storage"] = st

    # VTerm HTTP
    base = (vterm_http_base or cfg.vterm_http_base or "http://127.0.0.1:8765").rstrip("/")
    vth = {"base": base, "ok": False}
    try:
        t0 = _perf()
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{base}/health", timeout=3) as r:
                vth["status"] = r.status
                vth["ok"] = (r.status == 200)
                vth["latency_ms"] = int((_perf() - t0) * 1000)
                try:
                    payload = await r.json()
                    vth["payload"] = payload
                except Exception:
                    vth["payload"] = (await r.text())[:200]
    except Exception as e:
        vth["error"] = str(e)
    report["vterm_http"] = vth

    # RabbitMQ
    rmq = {"ok": False}
    try:
        m = RabbitMQManager()
        ok = m.connect()
        rmq["ok"] = bool(ok)
        if hasattr(m, "connection") and m.connection:
            rmq["is_closed"] = getattr(m.connection, "is_closed", None)
        m.close()
    except Exception as e:
        rmq["error"] = str(e)
    report["rabbitmq"] = rmq

    return report


def evaluate_health_gates(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Evaluate simple health gates and return (ok, reasons).

    Gates:
    - cookies: count > 0 and 'auth_token' present
    - storage: exists and cookie_count > 0
    - vterm_http: ok True
    - rabbitmq: ok True
    """
    reasons: List[str] = []
    ok = True

    ck = report.get("cookies", {})
    if not (int(ck.get("count", 0)) > 0 and ("auth_token" in set(ck.get("keys_present", [])))):
        ok = False
        reasons.append("cookies")

    st = report.get("storage", {})
    if not (bool(st.get("exists")) and int(st.get("cookie_count", 0)) > 0):
        ok = False
        reasons.append("storage")

    vt = report.get("vterm_http", {})
    if not bool(vt.get("ok")):
        ok = False
        reasons.append("vterm_http")

    rmq = report.get("rabbitmq", {})
    if not bool(rmq.get("ok")):
        ok = False
        reasons.append("rabbitmq")

    return ok, reasons
