#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from typing import Any as _Moved
import os
from typing import Dict

from cz_vterm_rabbitmq_daemon import RabbitMQBridge


async def post_reply_safari(reply_url: str, reply_text: str, author: str = "") -> bool:
    bridge = RabbitMQBridge()
    await bridge.initialize()
    try:
        data: Dict[str, str] = {
            "notification_id": "manual",
            "reply_url": reply_url,
            "reply_text": reply_text,
            "author": author or "user",
        }
        ok = await bridge.post_reply_to_twitter(data)
        return ok
    finally:
        await bridge.cleanup()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: quick_reply_safari.py <reply_url> <reply_text>")
        sys.exit(2)
    url = sys.argv[1]
    text = " ".join(sys.argv[2:])
    # Force Safari-like headless engine
    os.environ.setdefault("BROWSER_NAME", "webkit")
    ok = asyncio.run(post_reply_safari(url, text))
    print({"ok": ok})
