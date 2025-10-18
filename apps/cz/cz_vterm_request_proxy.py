#!/usr/bin/env python3
"""
VTerm Request Proxy Manager
Consumes cz_reply_request messages from RabbitMQ, calls VTerm (Claude) to craft
CZ persona replies, and publishes cz_reply_generated responses.
"""

import asyncio
import json
import logging
from typing import Any as _Moved
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from xbot.rabbitmq_manager import RabbitMQManager, BotMessage

# Reuse ClaudeGen pipeline from xbot.auto_responder
from xbot.auto_responder import ClaudeGen

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [VTERM-PROXY] %(levelname)s: %(message)s')
logger = logging.getLogger('vterm_proxy')


class VTermRequestProxy:
    def __init__(self, vterm_base: str = "http://127.0.0.1:9876", vterm_token: Optional[str] = None, system_path: str = "CLAUDE.md"):
        self.mq = RabbitMQManager()
        self.mq.connect()
        self.vterm = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=Path(system_path).read_text(encoding='utf-8') if Path(system_path).exists() else "", mode="run-pipe")

        # Register handler for cz_reply_request
        self.mq.register_handler("cz_reply_request", self._on_request)

    def start(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        try:
            await self.vterm.ensure_ready()
        except Exception:
            logger.warning("VTerm HTTP not responding yet; continuing and retrying on demand")
        # Blocking consume
        self.mq.consume_requests()

    def _on_request(self, message: BotMessage) -> None:
        data = message.data or {}
        post_url = str(data.get('post_url') or '')
        post_id = data.get('post_id')
        author = str(data.get('author_handle') or '')
        content = str(data.get('content') or '')
        if not post_url:
            logger.warning("cz_reply_request missing post_url; skipping")
            return
        # Build minimal PostEvent-like proxy for ClaudeGen.reply
        from dataclasses import dataclass
        from datetime import datetime
        @dataclass
        class _P:
            author: str = author
            author_handle: str = author
            content: str = content or (f"Craft a CZ reply to this tweet: {post_url}")
            timestamp: datetime = datetime.now()
        reply_text = ""
        try:
            loop = asyncio.new_event_loop()
            reply_text = loop.run_until_complete(self.vterm.reply(_P()))  # type: ignore[arg-type]
            loop.close()
        except Exception as e:
            logger.error(f"VTerm generation failed: {e}")
            reply_text = "4"
        reply_text = (reply_text or "4").strip()[:280]
        ok = self.mq.publish_cz_reply_generated(post_url=post_url, post_id=post_id, author_handle=author, content=content, reply_text=reply_text)
        if ok:
            logger.info(f"Generated reply for {post_id or post_url}: {reply_text[:100]}...")


if __name__ == "__main__":
    import os
    base = os.getenv('VTERM_HTTP_BASE', 'http://127.0.0.1:9876')
    token = os.getenv('VTERM_TOKEN')
    proxy = VTermRequestProxy(vterm_base=base, vterm_token=token, system_path='CLAUDE.md')
    proxy.start()
