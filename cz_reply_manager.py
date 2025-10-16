#!/usr/bin/env python3
"""
CZ Reply Manager
Consumes cz_reply_generated messages from RabbitMQ and posts replies on X in
headless mode using the 4botbsc session (cookies/storage state).
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from rabbitmq_manager import RabbitMQManager, BotMessage

from xbot.config import Config
from xbot.facade import XBot
from xbot.profiles import profile_paths

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [CZ-REPLY] %(levelname)s: %(message)s')
logger = logging.getLogger('cz_reply_mgr')


class CZReplyManager:
    def __init__(self, profile: str = "4botbsc"):
        self.mq = RabbitMQManager()
        self.mq.connect()
        self.profile = profile
        self.cfg = Config.from_env()
        # headless + persistent (so storageState is used); prefer config/profiles/<name>
        self.cfg.headless = True
        self.cfg.persist_session = True
        cfg_storage = Path("config/profiles") / profile / "storageState.json"
        if cfg_storage.exists():
            self.cfg.storage_state = cfg_storage
            self.cfg.user_data_dir = Path(".x-user") / profile
        else:
            s, u = profile_paths(profile)
            self.cfg.storage_state = s
            self.cfg.user_data_dir = u
        if not self.cfg.user_agent:
            self.cfg.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.bot = XBot(self.cfg)
        # register consumer handler
        self.mq.register_handler("cz_reply_generated", self._on_generated)

    def start(self) -> None:
        logger.info(f"Starting CZReplyManager for profile={self.profile}")
        self.mq.consume_responses()

    def _on_generated(self, message: BotMessage) -> None:
        data = message.data or {}
        post_url = str(data.get('post_url') or '')
        post_id = data.get('post_id')
        reply_text = str(data.get('reply_text') or '')
        if not post_url or not reply_text:
            logger.warning("cz_reply_generated missing url or text; skipping")
            return
        logger.info(f"Posting reply -> {post_url}: {reply_text[:100]}...")
        try:
            asyncio.run(self.bot.reply(post_url, reply_text))
            logger.info("✅ Reply posted")
        except Exception as e:
            logger.error(f"❌ Failed to post reply: {e}")


if __name__ == "__main__":
    mgr = CZReplyManager(profile=os.getenv('PROFILE', '4botbsc'))
    mgr.start()

