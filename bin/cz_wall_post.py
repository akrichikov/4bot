from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from xbot.config import Config
from xbot.facade import XBot
from xbot.profiles import profile_paths


def pick_storage(profile: str) -> tuple[Path, Path]:
    # Prefer config/profiles/<name>/storageState.json if present; else auth/<name>/storageState.json
    cfg_storage = Path("config/profiles") / profile / "storageState.json"
    auth_storage, user_dir_default = profile_paths(profile)
    if cfg_storage.exists():
        user_dir = Path(".x-user") / profile
        return cfg_storage, user_dir
    return auth_storage, user_dir_default


def cz_posts() -> List[str]:
    base = [
        "4. Less noise, more signal. BUIDL.",
        "4. Winners focus on building.",
        "4. Zoom out. Long-term > short-term.",
        "4. Keep users #SAFU. Deliver.",
        "4. Resilience compounds. Ship daily.",
        "4. Ignore FUD. Help builders.",
        "4. Execution beats speculation.",
        "4. Do the right thing. Always.",
        "4. Markets cycle. Builders persist.",
        "4. Simplicity > complexity. Focus.",
        "4. Respect the market. Keep building.",
        "4. Trust grows from consistent actions.",
        "4. Less talk, more code.",
        "4. Builders > FUDers.",
        "4. Risk management first."
    ]
    out: List[str] = []
    # repeat with light variation until we get 20
    i = 0
    while len(out) < 20:
        t = base[i % len(base)]
        suffix = " — CZ-inspired"
        text = f"{t} {suffix}"
        if len(text) > 240:
            text = text[:238]
        out.append(text)
        i += 1
    return out


async def main(
    profile: str = "4botbsc",
    x_user: str | None = "4botbsc@gmail.com",
    count: int = 20,
    min_interval_s: int = 120,
    max_interval_s: int = 180,
    headless: bool = True,
    dry_run: bool = False,
) -> None:
    if x_user:
        os.environ["X_USER"] = x_user
    cfg = Config.from_env()
    cfg.headless = headless
    cfg.persist_session = True
    storage, udir = pick_storage(profile)
    cfg.storage_state = storage
    cfg.user_data_dir = udir

    bot = XBot(cfg)
    posts = cz_posts()[:count]

    status_dir = Path("Docs/status")
    status_dir.mkdir(parents=True, exist_ok=True)
    run_md = status_dir / f"{datetime.now().date()}_cz_wall_post_run.md"
    with run_md.open("a", encoding="utf-8") as f:
        f.write(f"# CZ-inspired Wall Post Run {datetime.now().isoformat()}\n")
        f.write(f"profile={profile} storage={storage} user_dir={udir}\n\n")

    for i, text in enumerate(posts):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {i+1}/{count} -> {text}"
        print(line)
        with run_md.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        if not dry_run:
            await bot.post(text)
        if i < count - 1:
            await asyncio.sleep(random.randint(min_interval_s, max_interval_s))


if __name__ == "__main__":
    asyncio.run(main())
