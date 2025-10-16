from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiohttp

from .config import Config
from .browser import Browser
from .flows.login import login_if_needed
from .event_interceptor import EventInterceptor, PostEvent
from .facade import XBot

logger = logging.getLogger(__name__)


@dataclass
class ClaudeGen:
    base: str
    token: Optional[str] = None
    system_prompt: str = ""
    mode: str = "run-pipe"  # or 'write-read'

    async def _headers(self):
        return {"X-VTerm-Token": self.token} if self.token else None

    async def ensure_ready(self) -> None:
        async with aiohttp.ClientSession() as s:
            for _ in range(50):
                try:
                    async with s.get(f"{self.base}/health") as r:
                        if r.status == 200:
                            return
                except Exception:
                    await asyncio.sleep(0.1)
        raise RuntimeError("vterm http server not responding")

    async def launch_claude(self) -> None:
        if self.mode == "write-read":
            async with aiohttp.ClientSession(headers=await self._headers()) as s:
                # Start REPL
                await s.post(f"{self.base}/write", json={"text": "claude --dangerously-skip-permissions\n"})
                await asyncio.sleep(0.2)

    async def reply(self, post: PostEvent) -> str:
        prompt = f"Write a concise, helpful reply to this X post. Keep under 240 chars.\n\nAuthor:@{post.author_handle}\nContent:{post.content}\n"
        if self.mode == "run-pipe":
            # Use a one-shot invocation via /run
            cmd = (
                "printf %s " + shlex.quote(self.system_prompt) +
                " | claude --dangerously-skip-permissions --system - --message " + shlex.quote(prompt)
            )
            async with aiohttp.ClientSession(headers=await self._headers()) as s:
                async with s.post(f"{self.base}/run", json={"cmd": cmd, "timeout": 30}) as r:
                    data = await r.json()
                    lines = data.get("lines") or []
                    text = "\n".join(lines).strip()
                    return text[-240:] if text else ""
        else:
            # interactive write/read
            async with aiohttp.ClientSession(headers=await self._headers()) as s:
                msg = f"system:\n{self.system_prompt}\nuser:\n{prompt}\n"
                await s.post(f"{self.base}/write", json={"text": msg + "\n"})
                await asyncio.sleep(0.5)
                # collect output briefly
                chunks = []
                for _ in range(10):
                    async with s.get(f"{self.base}/read", params={"timeout":"0.2"}) as rd:
                        d = await rd.json()
                        lines = d.get("lines") or []
                        chunks.append("\n".join(lines))
                    await asyncio.sleep(0.1)
                text = "\n".join(chunks).strip()
                return text[-240:] if text else ""


def _cz_short_reply(post: PostEvent) -> str:
    base = [
        "Less noise, more signal. BUIDL.",
        "4. Back to building.",
        "Security first. #SAFU",
        "Play the long game.",
        "Winners focus on winning.",
        "Stop complaining, start building.",
    ]
    tail = f" — @{post.author_handle}" if post.author_handle else ""
    msg = base[hash(post.id) % len(base)]
    text = f"{msg}{tail}"
    return text[:240]


async def _monitor_pages(cfg: Config, claude: ClaudeGen, handle: str) -> None:
    bot = XBot(cfg)
    cfg.persist_session = False
    async with Browser(cfg, label="auto_responder") as b:
        page = b.page
        await login_if_needed(page, cfg)
        await page.goto(cfg.base_url + "/home", wait_until="domcontentloaded")

        inter = EventInterceptor()

        async def on_post(post: PostEvent):
            try:
                # Reply to any post that is NOT authored by our own handle
                if handle and post.author_handle and post.author_handle.lower() == handle.lower():
                    return
                # Skip obvious retweets (optional safety)
                if post.is_retweet:
                    return
                text = await claude.reply(post)
                if not text:
                    text = _cz_short_reply(post)
                if text:
                    status_url = f"{cfg.base_url.rstrip('/')}/i/web/status/{post.id}"
                    await bot.reply(status_url, text)
                    logger.info("Replied to %s (@%s)", post.id, post.author_handle)
            except Exception as e:
                logger.exception("Failed to auto-reply: %s", e)

        inter.add_callback(on_post)
        await inter.start_monitoring(page)

        # Optionally monitor notifications in a second page
        notif = await b._ctx.new_page()  # type: ignore[attr-defined]
        await notif.goto(cfg.base_url + "/notifications", wait_until="domcontentloaded")
        inter2 = EventInterceptor()
        inter2.add_callback(on_post)
        await inter2.start_monitoring(notif)

        # Run indefinitely
        while True:
            await asyncio.sleep(1.0)


def run(
    profile: str = "default",
    vterm_base: str = "http://127.0.0.1:9876",
    vterm_token: Optional[str] = None,
    system_path: str = "CLAUDE.md",
    vterm_mode: str = "run-pipe",
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = Config.from_env()
    # Headless, in-memory (non-persistent) session by default
    cfg.headless = True
    cfg.persist_session = False
    # Configure profile
    from .profiles import profile_paths
    s, u = profile_paths(profile)
    cfg.storage_state = s
    cfg.user_data_dir = u
    # handle for reply targeting
    handle = (cfg.handle or os.getenv("X_HANDLE") or "")

    # Load system prompt
    sys_path = Path(system_path)
    system_prompt = sys_path.read_text(encoding="utf-8") if sys_path.exists() else ""

    claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode=vterm_mode)

    async def _main():
        # Try to ensure vterm http is ready; fall back to local templates
        try:
            await claude.ensure_ready()
            if vterm_mode == "write-read":
                await claude.launch_claude()
        except Exception:
            logger.warning("vterm http not available; falling back to local CZ templates")
            claude.mode = "local"  # type: ignore[attr-defined]
        await _monitor_pages(cfg, claude, handle)

    asyncio.run(_main())


if __name__ == "__main__":
    # Basic arg shim
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default="default")
    p.add_argument("--vterm-base", default="http://127.0.0.1:9876")
    p.add_argument("--vterm-token", default=None)
    p.add_argument("--system-path", default="CLAUDE.md")
    p.add_argument("--vterm-mode", default="run-pipe")
    a = p.parse_args()
    run(a.profile, a.vterm_base, a.vterm_token, a.system_path, a.vterm_mode)
