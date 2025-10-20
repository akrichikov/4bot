from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

import aiohttp


async def fetch_json(sess: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    async with sess.get(url) as r:
        try:
            return await r.json()
        except Exception:
            return {"status": r.status, "text": await r.text()}


async def main() -> int:
    base = os.environ.get("VT_BASE", f"http://127.0.0.1:{os.environ.get('PTY_PORT','9876')}")
    out = Path(os.environ.get("VT_OUT", "Docs/status/vterm_snapshot.json"))
    to = aiohttp.ClientTimeout(total=5.0)
    async with aiohttp.ClientSession(timeout=to) as sess:
        version = await fetch_json(sess, base.rstrip('/') + "/version")
        health = await fetch_json(sess, base.rstrip('/') + "/health")
        ready = await fetch_json(sess, base.rstrip('/') + "/ready")
        config = await fetch_json(sess, base.rstrip('/') + "/config")
        # metrics trimmed: only first 2KB to avoid large files
        async with sess.get(base.rstrip('/') + "/metrics") as r:
            metrics = (await r.text())[:2048]
    snapshot: Dict[str, Any] = {
        "base": base,
        "version": version,
        "health": health,
        "ready": ready,
        "config": config,
        "metrics_excerpt": metrics,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

