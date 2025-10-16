from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from xbot.config import Config
from xbot.browser import Browser
from xbot.flows.login import is_logged_in
from xbot.facade import XBot


@dataclass
class Args:
    url: str
    text: str
    profile: str = "4botbsc"
    timeout_s: int = 900
    poll_s: float = 2.0


async def wait_for_session(cfg: Config, timeout_s: int, poll_s: float) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with Browser(cfg, label="session_check") as b:
                await b.page.goto(cfg.base_url, wait_until="domcontentloaded")
                if await is_logged_in(b.page):
                    return True
        except Exception:
            pass
        await asyncio.sleep(poll_s)
    return False


async def main(a: Args) -> None:
    # honor overlay profile paths
    cfg = Config.from_env()
    cfg.profile_name = a.profile
    # Verify session
    ok = await wait_for_session(cfg, a.timeout_s, a.poll_s)
    if not ok:
        raise SystemExit("session not ready within timeout")
    # Post reply
    bot = XBot(cfg)
    await bot.reply(a.url, a.text)
    print("Reply posted.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--profile", default="4botbsc")
    p.add_argument("--timeout-s", type=int, default=900)
    p.add_argument("--poll-s", type=float, default=2.0)
    ar = p.parse_args()
    asyncio.run(main(Args(url=ar.url, text=ar.text, profile=ar.profile, timeout_s=ar.timeout_s, poll_s=ar.poll_s)))
