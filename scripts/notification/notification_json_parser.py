#!/usr/bin/env python3
"""
Thin CLI wrapper delegating to canonical xbot.notification_json_parser.
"""

import asyncio
import argparse
from pathlib import Path
import sys


def main() -> int:
    # Ensure package root is importable when executed directly
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from xbot.notification_json_parser import NotificationJSONParser  # noqa: WPS433,E402

    ap = argparse.ArgumentParser(description="X/Twitter notification JSON parser")
    ap.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    args = ap.parse_args()

    async def _run():
        parser = NotificationJSONParser()
        await parser.parse_notifications(duration=args.duration)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

