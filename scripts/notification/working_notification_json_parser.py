#!/usr/bin/env python3
"""
Legacy wrapper delegating to xbot.notification_json_parser (canonical).
"""

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xbot.notification_json_parser import NotificationJSONParser  # noqa: E402


async def _run():
    parser = NotificationJSONParser()
    await parser.parse_notifications(duration=60)


if __name__ == "__main__":
    asyncio.run(_run())
