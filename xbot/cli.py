from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich import print

from pathlib import Path
from .config import Config
from .facade import XBot
from .browser import Browser
from .flows.login import login_if_needed, is_logged_in
from .state import export_storage_state, apply_storage_state
from .playbook import run_playbook
from .health import run_selector_health
from .health import tweet_state as health_tweet_state, compose_health as health_compose
from .scheduler import run_schedule
from .report import summary as report_summary, export_csv as report_export_csv
from .profiles import profile_paths, list_profiles, ensure_profile_dirs, clear_state


app = typer.Typer(no_args_is_help=True, add_completion=False)
cookies_app = typer.Typer(no_args_is_help=True, add_completion=False)
session_app = typer.Typer(no_args_is_help=True, add_completion=False)
play_app = typer.Typer(no_args_is_help=True, add_completion=False)
health_app = typer.Typer(no_args_is_help=True, add_completion=False)
schedule_app = typer.Typer(no_args_is_help=True, add_completion=False)
report_app = typer.Typer(no_args_is_help=True, add_completion=False)
profile_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(cookies_app, name="cookies", help="Import/export storage state")
app.add_typer(session_app, name="session", help="Session utilities")
app.add_typer(play_app, name="queue", help="Run playbooks (JSON sequence of actions)")
app.add_typer(health_app, name="health", help="Health checks and diagnostics")
app.add_typer(schedule_app, name="schedule", help="Schedule playbooks by times-of-day")
app.add_typer(report_app, name="report", help="Summaries and exports for results")
app.add_typer(profile_app, name="profile", help="Manage named profiles (sessions)")


def _cfg(
    headless: bool = typer.Option(True, help="Run headless"),
    persist_session: bool = typer.Option(True, help="Persist session/cookies"),
    storage_state: str = typer.Option("auth/storageState.json", help="Storage state path"),
    user_data_dir: str = typer.Option(".x-user", help="User data dir (persistent context)"),
    proxy_url: Optional[str] = typer.Option(None, help="Proxy URL (e.g. http://user:pass@host:port)"),
    profile: str = typer.Option("default", help="Named profile for session separation"),
) -> Config:
    base = Config.from_env()
    base.headless = headless
    base.persist_session = persist_session
    if storage_state == "auth/storageState.json" and user_data_dir == ".x-user":
        s, u = profile_paths(profile)
        base.storage_state = s
        base.user_data_dir = u
    else:
        base.storage_state = Path(storage_state)
        base.user_data_dir = Path(user_data_dir)
    base.proxy_url = proxy_url or base.proxy_url
    base.profile_name = profile
    return base


@app.command()
def login(
    headless: bool = True,
    persist_session: bool = True,
    storage_state: str = "auth/storageState.json",
    user_data_dir: str = ".x-user",
    proxy_url: Optional[str] = None,
    profile: str = "default",
) -> None:
    cfg = _cfg(headless, persist_session, storage_state, user_data_dir, proxy_url, profile)

    async def _run() -> None:
        async with Browser(cfg) as b:
            await login_if_needed(b.page, cfg)
            print("[green]Login verified and session stored.[/green]")

    asyncio.run(_run())


@app.command()
def post(text: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.post(text))
    print("[green]Post submitted.[/green]")


@app.command()
def reply(url: str, text: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.reply(url, text))
    print("[green]Reply submitted.[/green]")


@app.command("post-media")
def post_media(
    text: str,
    files: list[Path] = typer.Argument(..., help="One or more image files"),
) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.post_media(text, [str(p) for p in files]))
    print("[green]Post with media submitted.[/green]")


@app.command()
def follow(profile_url: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.follow(profile_url))
    print("[green]Follow clicked.[/green]")


@app.command()
def unfollow(profile_url: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.unfollow(profile_url))
    print("[green]Unfollow clicked.[/green]")


@app.command()
def dm(profile_url: str, text: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.dm(profile_url, text))
    print("[green]DM sent.[/green]")


@app.command()
def like(url: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.like(url))
    print("[green]Like clicked.[/green]")


@app.command()
def retweet(url: str) -> None:
    bot = XBot(Config.from_env())
    asyncio.run(bot.retweet(url))
    print("[green]Retweet confirmed.[/green]")


@cookies_app.command("export")
def cookies_export(path: Path = Path("auth/storageState.json")) -> None:
    cfg = Config.from_env()
    cfg.storage_state = path

    async def _run() -> None:
        async with Browser(cfg) as b:
            await login_if_needed(b.page, cfg)
            await export_storage_state(b._ctx, cfg.storage_state)  # type: ignore[attr-defined]
            print(f"[green]Exported storage to {cfg.storage_state}[/green]")

    asyncio.run(_run())


@cookies_app.command("import")
def cookies_import(path: Path = Path("auth/storageState.json")) -> None:
    cfg = Config.from_env()
    cfg.storage_state = path

    async def _run() -> None:
        async with Browser(cfg) as b:
            await apply_storage_state(b._ctx, cfg.storage_state)  # type: ignore[attr-defined]
            print(f"[green]Imported storage from {cfg.storage_state}[/green]")

    asyncio.run(_run())


@cookies_app.command("merge-json")
def cookies_merge_json(
    src: Path,
    dest: Path = Path("auth/storageState.json"),
    filter_domain: str = typer.Option("x.com", help="Only import cookies for this domain (suffix match)"),
) -> None:
    from .cookies import load_cookie_json, merge_into_storage

    cookies = load_cookie_json(src)
    count = merge_into_storage(dest, cookies, [filter_domain, f".{filter_domain}", "twitter.com", ".twitter.com"]) 
    print(f"[green]Merged {count} cookies into {dest}[/green]")


@profile_app.command("list")
def profile_list() -> None:
    from rich import print as rprint
    rprint({"profiles": list_profiles()})


@profile_app.command("paths")
def profile_paths_cmd(name: str = typer.Argument("default")) -> None:
    s, u = profile_paths(name)
    print(f"storage_state: {s}\nuser_data_dir: {u}")


@profile_app.command("ensure")
def profile_ensure(name: str = typer.Argument("default")) -> None:
    s, u = ensure_profile_dirs(name)
    print(f"[green]Ensured dirs\n- storage: {s}\n- user: {u}[/green]")


@profile_app.command("clear-state")
def profile_clear_state(name: str = typer.Argument("default")) -> None:
    if clear_state(name):
        print("[green]Cleared storage state.[/green]")
    else:
        print("[yellow]No storage state to clear.[/yellow]")


@session_app.command("check")
def session_check() -> None:
    cfg = Config.from_env()

    async def _run() -> None:
        async with Browser(cfg) as b:
            await b.page.goto(cfg.base_url, wait_until="domcontentloaded")
            if await is_logged_in(b.page):
                print("[green]Session valid (logged in).[/green]")
            else:
                print("[yellow]Session not logged in.[/yellow]")

    asyncio.run(_run())


@play_app.command("run")
def queue_run(path: Path) -> None:
    cfg = Config.from_env()
    asyncio.run(run_playbook(path, cfg))
    print("[green]Playbook complete.[/green]")


@health_app.command("selectors")
def health_selectors(
    tweet_url: Optional[str] = typer.Option(None, help="A tweet/status URL or id to probe"),
    profile: Optional[str] = typer.Option(None, help="A profile handle or URL to probe"),
    json_out: Optional[Path] = typer.Option(None, help="Path to write JSON result"),
) -> None:
    cfg = Config.from_env()

    async def _run() -> None:
        report = await run_selector_health(cfg, tweet_url=tweet_url, profile=profile)
        from rich import print as rprint
        ok = "[green]PASS[/green]" if report.all_passed else "[red]FAIL[/red]"
        rprint(f"Selector health: {ok}")
        for r in report.results:
            status = "SKIP" if r.skipped else ("PASS" if r.passed else "FAIL")
            extra = f" - {r.detail}" if r.detail else ""
            rprint(f" - {r.name}: {status}{extra}")
        if json_out:
            import json
            data = {
                "all_passed": report.all_passed,
                "results": [r.__dict__ for r in report.results],
            }
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    asyncio.run(_run())


@health_app.command("tweet-state")
def health_tweet_state_cmd(url: str) -> None:
    cfg = Config.from_env()
    async def _run() -> None:
        data = await health_tweet_state(cfg, url)
        from rich import print as rprint
        rprint(data)
    asyncio.run(_run())


@health_app.command("compose")
def health_compose_cmd() -> None:
    cfg = Config.from_env()
    async def _run() -> None:
        data = await health_compose(cfg)
        from rich import print as rprint
        rprint(data)
    asyncio.run(_run())


@schedule_app.command("run")
def schedule_run(
    spec: Path,
    once: bool = typer.Option(False, help="Run only the next due item then exit"),
    dry_run: bool = typer.Option(False, help="Show the next due item and exit"),
) -> None:
    cfg = Config.from_env()
    asyncio.run(run_schedule(spec, cfg, once=once, dry_run=dry_run))
    if dry_run:
        print("[green]Dry run complete.[/green]")
    elif once:
        print("[green]Schedule once run complete.[/green]")
    else:
        print("[green]Schedule loop terminated.[/green]")


@report_app.command("summary")
def report_summary_cmd(index: Path = Path("artifacts/results/index.jsonl")) -> None:
    from rich import print as rprint
    data = report_summary(index)
    rprint(data)


@report_app.command("export-csv")
def report_export_csv_cmd(index: Path = Path("artifacts/results/index.jsonl"), out: Path = Path("artifacts/results/index.csv")) -> None:
    report_export_csv(index, out)
    print(f"[green]Wrote {out}[/green]")


if __name__ == "__main__":
    app()
