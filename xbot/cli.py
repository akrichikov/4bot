from __future__ import annotations

import asyncio
from typing import Optional, List

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
from .health import proxy_check as health_proxy_check
from .health import system_health as health_system
from .health import selectors_snapshot as health_selectors_snapshot, evaluate_snapshot as health_evaluate_snapshot, drift_hints as health_drift_hints
from .results import record_action_result
from .scheduler import run_schedule
from .report import summary as report_summary, export_csv as report_export_csv, check_threshold as report_check_threshold
from .report_html import html_report as report_html
from .report_health import write_system_health_html
from .profiles import profile_paths, list_profiles, ensure_profile_dirs, clear_state, set_overlay_value, del_overlay_key, read_overlay
from .vterm import VTerm
from .vtermd import VTermDaemon, client_request, DEFAULT_SOCKET
from .vterm_http import VTermHTTPServer
from .auto_responder import ClaudeGen
from apps.cz.cz_vterm_rabbitmq_daemon import CZVTermDaemon
import sys
import shlex
import json


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
vterm_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(vterm_app, name="vterm", help="In-memory PTY virtual terminal")
queue_app = typer.Typer(no_args_is_help=True, add_completion=False)
vterm_app.add_typer(queue_app, name="queue", help="HTTP queue operations (requires vterm http server)")
vtermd_app = typer.Typer(no_args_is_help=True, add_completion=False)
results_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(results_app, name="results", help="Inspect raw results index")


def _cfg(
    headless: bool = typer.Option(True, help="Run headless"),
    persist_session: bool = typer.Option(True, help="Persist session/cookies"),
    storage_state: str = typer.Option("auth/storageState.json", help="Storage state path"),
    user_data_dir: str = typer.Option(".x-user", help="User data dir (persistent context)"),
    proxy_url: Optional[str] = typer.Option(None, help="Proxy URL (e.g. http://user:pass@host:port)"),
    profile: str = typer.Option("default", help="Named profile for session separation"),
    browser: str = "chromium",
) -> Config:
    base = Config.from_env()
    base.headless = headless
    base.persist_session = persist_session
    base.browser_name = browser.lower()
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
    browser: str = "chromium",
    login_method: str = typer.Option("cookies", help="cookies|credentials|google"),
) -> None:
    cfg = _cfg(headless, persist_session, storage_state, user_data_dir, proxy_url, profile, browser)

    async def _run() -> None:
        cfg.browser_name = browser.lower()
        cfg.login_method = login_method.lower()  # type: ignore[assignment]
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


@app.command("cz-daemon")
def cz_daemon(
    vterm_host: str = typer.Option("127.0.0.1", help="VTerm HTTP host"),
    vterm_port: int = typer.Option(8765, help="VTerm HTTP port"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm token"),
) -> None:
    """Start the CZ VTerm RabbitMQ Daemon (headless)."""
    import asyncio, os
    if vterm_token:
        os.environ["VTERM_TOKEN"] = vterm_token
    os.environ["VTERM_HOST"] = vterm_host
    os.environ["VTERM_PORT"] = str(vterm_port)

    async def _run():
        daemon = CZVTermDaemon()
        try:
            await daemon.run()
        finally:
            await daemon.cleanup()

    asyncio.run(_run())


@app.command("fud-reply")
def fud_reply(
    profile: str = typer.Option("4botbsc", help="Profile name for 4bot account"),
    list_path: Path = typer.Option(Path("Docs/4Bot Tweets.md"), help="Markdown file with tweet URLs"),
    vterm_base: str = typer.Option("http://127.0.0.1:9876", help="VTerm HTTP base"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm HTTP token"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="Path to CZ system prompt"),
    mode: str = typer.Option("run-pipe", help="Claude mode: run-pipe|write-read (falls back to local)"),
    dry_run: bool = typer.Option(False, help="Do not post, only print planned replies"),
    x_user: Optional[str] = typer.Option(None, help="X username/email for login (overrides env)"),
    x_handle: Optional[str] = typer.Option(None, help="X handle (e.g., 4botbsc)"),
    headless: bool = typer.Option(True, help="Run headless (in-memory if persist_session disabled)"),
) -> None:
    import re, asyncio
    from .auto_responder import ClaudeGen
    from .profiles import profile_paths
    import os
    if x_user:
        os.environ['X_USER'] = x_user
    if x_handle:
        os.environ['X_HANDLE'] = x_handle
    cfg = Config.from_env()
    # honor headless selection and prefer persistent context to carry cookies/localStorage reliably
    cfg.headless = bool(headless)
    cfg.persist_session = True
    s, u = profile_paths(profile)
    cfg.storage_state = s
    cfg.user_data_dir = u

    text = list_path.read_text(encoding="utf-8")
    # Robust URL extraction, including markdown-style links and i/web/status patterns
    urls = re.findall(r"https?://(?:x\.com|twitter\.com)/[^/\s]+/status/\d+|https?://x\.com/i/web/status/\d+", text)
    # normalize URLs: strip trailing punctuation
    urls = [u.rstrip(').,;*]') for u in urls]
    # de-dup preserve order
    seen = set(); dedup = []
    for u in urls:
        if u not in seen:
            seen.add(u); dedup.append(u)

    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode=mode)

    def _cz_local(url: str) -> str:
        pool = [
            "Less noise, more signal. BUIDL.",
            "4. Back to building.",
            "Security first. #SAFU",
            "Play the long game.",
            "Winners focus on winning.",
            "Stop complaining, start building.",
            "Clear rules protect users and innovation.",
            "Utility > hype. Ship, learn, iterate.",
        ]
        return pool[hash(url) % len(pool)][:240]

    async def _run():
        use_local = False
        try:
            await claude.ensure_ready()
        except Exception:
            print("[yellow]vterm HTTP not available; using local CZ replies.[/yellow]")
            use_local = True
        from .browser import Browser
        from .flows.login import is_logged_in
        bot = XBot(cfg)
        async with Browser(cfg, label="fud_replier") as b:
            try:
                await b.page.goto(cfg.base_url + "/home", wait_until="domcontentloaded")
            except Exception:
                pass
            for url in dedup:
                # Navigate to collect context then reply
                try:
                    await b.page.goto(url, wait_until="domcontentloaded")
                except Exception:
                    pass
                # Build a synthetic PostEvent-like payload by scraping minimal content (optional)
                # For simplicity here, rely on Claude prompt with URL context
                from dataclasses import dataclass
                from datetime import datetime as _dt
                @dataclass
                class _P:  # minimal shape with required fields
                    author: str = ""
                    author_handle: str = cfg.handle or ""
                    content: str = f"Please open and read the tweet at {url} and reply as CZ."
                    timestamp: _dt = _dt.now()
                if not use_local:
                    try:
                        reply_text = await claude.reply(_P())
                        if not reply_text:
                            reply_text = _cz_local(url)
                    except Exception:
                        reply_text = _cz_local(url)
                else:
                    reply_text = _cz_local(url)
                print(f"[cyan]Reply to {url}:[/cyan] {reply_text}")
                if not dry_run:
                    await bot.reply(url, reply_text)
    asyncio.run(_run())


@app.command("cz-posts")
def cz_posts(
    count: int = typer.Option(20, help="Number of tweets to post"),
    min_interval_s: int = typer.Option(120, help="Minimum interval seconds"),
    max_interval_s: int = typer.Option(180, help="Maximum interval seconds"),
    profile: str = typer.Option("Profile 13", help="Chrome profile for 4bot account"),
    vterm_base: str = typer.Option("http://127.0.0.1:9876", help="VTerm HTTP base"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm token"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ system prompt path"),
    x_user: Optional[str] = typer.Option(None, help="X username/email"),
    x_handle: Optional[str] = typer.Option(None, help="X handle (e.g., 4botbsc)"),
    dry_run: bool = typer.Option(False, help="If true, do not post"),
) -> None:
    import os, random, time
    from datetime import datetime
    cfg = Config.from_env()
    # headless + in-memory (non-persistent)
    cfg.headless = True
    cfg.persist_session = False
    cfg.persist_session = False  # use ephemeral context to avoid profile lock; storageState applied
    if x_user:
        os.environ['X_USER'] = x_user
    if x_handle:
        os.environ['X_HANDLE'] = x_handle
    # reload cfg to capture env overrides
    cfg = Config.from_env()
    s, u = profile_paths(profile)
    cfg.storage_state = s
    cfg.user_data_dir = u
    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode="run-pipe")

    topics = [
        "Ignore FUD, keep building",
        "Builders over speculators",
        "Why '4' means focus",
        "Resilience during volatility",
        "Support the community",
        "Long-term conviction",
        "Shipping beats shouting",
        "Signal vs noise in crypto",
        "Market cycles and discipline",
        "What building looks like today",
    ]

    def build_prompt(topic: str) -> str:
        return (
            "Write a single original X (Twitter) post in the CZ persona that responds to this theme: "
            + topic + ". \n"
            "Constraints: 1) 240 characters max; 2) No links; 3) At most one hashtag (#IgnoreFUD optional); "
            "4) No emojis more than 1; 5) Vary phrasing each time; 6) Avoid repetition and quotes. "
            "Provide only the tweet text."
        )

    async def _once(bot: XBot, i: int) -> None:
        # pick a topic
        topic = random.choice(topics)
        # use Claude to generate
        text = await claude.reply(type("P", (), {"author":"","author_handle":cfg.handle or (x_handle or ""), "content": build_prompt(topic), "timestamp": datetime.now()})())
        text = (text or "4").strip()
        if len(text) > 280:
            text = text[:280]
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[{ts}] Post {i+1}/{count}: {text}")
        if not dry_run:
            await bot.post(text)

    async def _run_all():
        await claude.ensure_ready()
        bot = XBot(cfg)
        for i in range(count):
            try:
                await _once(bot, i)
            except Exception as e:
                print({"error": str(e)})
            if i < count - 1:
                delay = random.randint(min_interval_s, max_interval_s)
                time.sleep(delay)

    asyncio.run(_run_all())


@app.command("reply-all")
def reply_all(
    source: str = typer.Option("both", help="home|notifications|both"),
    max_replies: int = typer.Option(25, help="Max number of replies to send"),
    duration_s: int = typer.Option(120, help="Max monitoring seconds (ignored if max reached)"),
    min_delay_s: int = typer.Option(4, help="Minimum delay between replies (sec)"),
    max_delay_s: int = typer.Option(8, help="Maximum delay between replies (sec)"),
    profile: str = typer.Option("Profile 13", help="Chrome profile for 4bot account"),
    vterm_base: str = typer.Option("http://127.0.0.1:9876", help="VTerm HTTP base"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm token"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ system prompt path"),
    x_user: Optional[str] = typer.Option(None, help="X username/email"),
    x_handle: Optional[str] = typer.Option(None, help="X handle (e.g., 4botbsc)"),
    dry_run: bool = typer.Option(False, help="If true, do not post"),
) -> None:
    import os, random, time
    from datetime import datetime
    from .event_interceptor import EventInterceptor, PostEvent
    from .flows.login import is_logged_in
    from .profiles import profile_paths

    if x_user:
        os.environ['X_USER'] = x_user
    if x_handle:
        os.environ['X_HANDLE'] = x_handle
    cfg = Config.from_env()
    cfg.headless = True
    cfg.persist_session = False
    s, u = profile_paths(profile)
    cfg.storage_state = s
    cfg.user_data_dir = u

    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode="run-pipe")

    async def _run():
        await claude.ensure_ready()
        bot = XBot(cfg)
        replied: set[str] = set()
        cutoff = time.time() + duration_s
        async with Browser(cfg, label="reply_all") as b:
            # open sources
            pages = []
            await b.page.goto(cfg.base_url + "/home", wait_until="domcontentloaded")
            pages.append(b.page)
            if source in ("notifications","both"):
                notif = await b._ctx.new_page()  # type: ignore[attr-defined]
                await notif.goto(cfg.base_url + "/notifications", wait_until="domcontentloaded")
                pages.append(notif)

            inters: list[EventInterceptor] = []
            for p in pages:
                inter = EventInterceptor()
                inters.append(inter)
                await inter.start_monitoring(p)

            i = 0
            while i < max_replies and time.time() < cutoff:
                # gather across interceptors
                for inter in inters:
                    # internal buffer is private; rely on callbacks by attaching a lightweight queue
                    pass
                # Instead, use a small JS scrape every loop for robustness
                for p in pages:
                    try:
                        data = await p.evaluate("""
                            () => Array.from(document.querySelectorAll('article a[href*="/status/"]'))
                                      .slice(0,20)
                                      .map(a => a.href)
                        """)
                    except Exception:
                        data = []
                    if not data:
                        continue
                    for href in data:
                        try:
                            sid = href.split('/status/')[1].split('?')[0]
                        except Exception:
                            continue
                        if sid in replied:
                            continue
                        # skip self posts
                        # Try to detect author handle on card
                        author_handle = ""
                        try:
                            author_handle = await p.evaluate("""
                                (href) => {
                                    const a = Array.from(document.querySelectorAll('a[href*="/status/"]')).find(x => x.href === href);
                                    const root = a?.closest('article');
                                    const h = root?.querySelector('[data-testid="User-Name"] a[href^="/"]');
                                    return h ? h.href.split('/').pop() : '';
                                }
                            """, href)
                        except Exception:
                            author_handle = ""
                        my_handle = cfg.handle or (x_handle or "")
                        if my_handle and author_handle and author_handle.lower() == my_handle.lower():
                            continue
                        # Build prompt for Claude CZ reply
                        content_hint = f"Read the tweet at {href} and reply as CZ (from CLAUDE.md)."
                        class _P: pass
                        ptmp = _P(); ptmp.author = ''; ptmp.author_handle = my_handle; ptmp.content = content_hint; ptmp.timestamp = datetime.now()
                        reply_text = await claude.reply(ptmp)  # type: ignore[arg-type]
                        reply_text = (reply_text or "4").strip()
                        if len(reply_text) > 280:
                            reply_text = reply_text[:280]
                        print(f"Replying to {href}: {reply_text}")
                        if not dry_run:
                            await bot.reply(href, reply_text)
                        replied.add(sid)
                        i += 1
                        if i >= max_replies:
                            break
                        time.sleep(random.randint(min_delay_s, max_delay_s))
                    if i >= max_replies or time.time() >= cutoff:
                        break
                await asyncio.sleep(0.3)

    asyncio.run(_run())


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


@profile_app.command("show")
def profile_show(name: str = typer.Argument("default")) -> None:
    from rich import print as rprint
    s, u = profile_paths(name)
    rprint({"profile": name, "storage_state": str(s), "user_data_dir": str(u), "overlay": read_overlay(name)})


@profile_app.command("set-proxy")
def profile_set_proxy(name: str, proxy_url: str) -> None:
    set_overlay_value(name, "proxy_url", proxy_url)
    print("[green]Set proxy_url.[/green]")


@profile_app.command("unset-proxy")
def profile_unset_proxy(name: str) -> None:
    if del_overlay_key(name, "proxy_url"):
        print("[green]Unset proxy_url.[/green]")
    else:
        print("[yellow]proxy_url not set.[/yellow]")


@profile_app.command("set-locale")
def profile_set_locale(name: str, locale: str) -> None:
    set_overlay_value(name, "locale", locale)
    print("[green]Set locale.[/green]")


@profile_app.command("set-timezone")
def profile_set_timezone(name: str, tz: str) -> None:
    set_overlay_value(name, "timezone_id", tz)
    print("[green]Set timezone_id.[/green]")


@profile_app.command("set-ua")
def profile_set_ua(name: str, user_agent: str) -> None:
    set_overlay_value(name, "user_agent", user_agent)
    print("[green]Set user_agent.[/green]")


@profile_app.command("set-viewport")
def profile_set_viewport(name: str, width: int, height: int) -> None:
    set_overlay_value(name, "viewport_width", width)
    set_overlay_value(name, "viewport_height", height)
    print("[green]Set viewport.[/green]")


@profile_app.command("proxy-check")
def profile_proxy_check(
    name: str = typer.Argument("default"),
    url: str = typer.Option("https://api.ipify.org?format=json", help="Check URL (e.g., ipify/httpbin)")
) -> None:
    cfg = Config.from_env()
    cfg.profile_name = name
    # Recompute storage/user_data for the profile
    s, u = profile_paths(name)
    cfg.storage_state = s
    cfg.user_data_dir = u

    async def _run() -> None:
        from .browser import Browser
        async with Browser(cfg, label="proxy_check") as b:
            await b.page.goto(url, wait_until="domcontentloaded")
            txt = await b.page.text_content("body")
            from rich import print as rprint
            rprint({"url": url, "body": (txt or "").strip()[:500]})

    asyncio.run(_run())


@vterm_app.command("run")
def vterm_run(
    cmd: List[str] = typer.Argument(..., help="Command and args to execute in PTY"),
    timeout: float = typer.Option(10.0, help="Timeout in seconds"),
) -> None:
    command = " ".join(shlex.quote(c) for c in cmd)
    vt = VTerm()
    try:
        res = vt.run(command, timeout=timeout)
        sys.stdout.write(res.to_json() + "\n")
    finally:
        vt.close()


@vterm_app.command("server")
def vterm_server(
    timeout: float = typer.Option(10.0, help="Default timeout in seconds per command"),
) -> None:
    """Read JSON lines from stdin: {"cmd": "...", "timeout": 5.0}. Emit JSON per line."""
    vt = VTerm()
    try:
        vt.start()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                cmd = str(req.get("cmd", "")).strip()
                t = float(req.get("timeout", timeout))
                if not cmd:
                    raise ValueError("missing cmd")
                res = vt.run(cmd, timeout=t)
                sys.stdout.write(res.to_json() + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(json.dumps({"error": str(e)}) + "\n")
                sys.stdout.flush()
    finally:
        vt.close()


@vterm_app.command("http")
def vterm_http(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(9876, help="Bind port"),
    token: str | None = typer.Option(None, help="Shared token required in X-VTerm-Token header"),
    rate_qps: float | None = typer.Option(None, help="Rate limit QPS (per token/IP)"),
    rate_burst: int = typer.Option(5, help="Rate limit burst"),
    audit_log: Path | None = typer.Option(None, help="Append JSONL audit here"),
    audit: bool = typer.Option(False, help="Enable request audit logging"),
    admin_token: str | None = typer.Option(None, help="Admin token for /admin/shutdown"),
) -> None:
    server = VTermHTTPServer(host=host, port=port, token=token, admin_token=admin_token, rate_qps=rate_qps, rate_burst=rate_burst, audit_log=audit_log, audit_enabled=audit)
    server.run()


@vterm_app.command("client")
def vterm_client(
    mode: str = typer.Argument("http", help="http|unix"),
    target: str = typer.Option("http://127.0.0.1:9876", help="Base URL (http) or socket path (unix)"),
    token: str | None = typer.Option(None, help="Token for HTTP mode"),
    run: str | None = typer.Option(None, help="Command to run"),
    write: str | None = typer.Option(None, help="Text to write"),
    read_timeout: float = typer.Option(0.25, help="Read timeout"),
    admin_shutdown: bool = typer.Option(False, help="Call /admin/shutdown (HTTP mode)"),
    admin_token: str | None = typer.Option(None, help="Admin token for shutdown"),
) -> None:
    from .vterm_client import VTermClient
    import asyncio as _asyncio

    if mode == "http":
        client = VTermClient(mode="http", base=target, token=token)
        async def _go():
            import sys as _sys, json as _json
            import aiohttp as _aio
            if admin_shutdown:
                headers = {"X-VTerm-Admin": admin_token} if admin_token else {}
                async with _aio.ClientSession(headers=headers) as s:
                    async with s.post(f"{target}/admin/shutdown") as r:
                        _sys.stdout.write(_json.dumps({"status": r.status, "body": await r.json()}) + "\n"); return
            if run:
                resp = await client.run_http(run)
                _sys.stdout.write(_json.dumps(resp) + "\n"); return
            if write is not None:
                resp = await client.write_http(write)
                _sys.stdout.write(_json.dumps(resp) + "\n"); return
            resp = await client.read_http(read_timeout)
            _sys.stdout.write(_json.dumps(resp) + "\n")
        _asyncio.run(_go())
    elif mode == "unix":
        client = VTermClient(mode="unix", socket_path=target)
        import json as _json, sys as _sys
        if run:
            _sys.stdout.write(_json.dumps(client.run_unix(run)) + "\n"); return
        if write is not None:
            _sys.stdout.write(_json.dumps(client.write_unix(write)) + "\n"); return
        _sys.stdout.write(_json.dumps(client.read_unix(read_timeout)) + "\n")
    else:
        raise typer.Exit(code=2)


@queue_app.command("run")
def vterm_queue_run(
    cmd: List[str] = typer.Argument(..., help="Command and args to enqueue"),
    target: str = typer.Option("http://127.0.0.1:9876", help="HTTP base URL"),
    token: str | None = typer.Option(None, help="X-VTerm-Token for auth"),
) -> None:
    import aiohttp, asyncio as _asyncio, json as _json, sys as _sys
    async def _go():
        headers = {"X-VTerm-Token": token} if token else None
        body = {"cmd": " ".join(shlex.quote(c) for c in cmd)}
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.post(f"{target}/queue/run", json=body) as r:
                _sys.stdout.write(_json.dumps({"status": r.status, **(await r.json())}) + "\n")
    _asyncio.run(_go())


@queue_app.command("get")
def vterm_queue_get(
    job_id: int = typer.Argument(..., help="Job id"),
    target: str = typer.Option("http://127.0.0.1:9876", help="HTTP base URL"),
    token: str | None = typer.Option(None, help="X-VTerm-Token for auth"),
) -> None:
    import aiohttp, asyncio as _asyncio, json as _json, sys as _sys
    async def _go():
        headers = {"X-VTerm-Token": token} if token else None
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(f"{target}/queue/{job_id}") as r:
                _sys.stdout.write(_json.dumps({"status": r.status, **(await r.json())}) + "\n")
    _asyncio.run(_go())


@queue_app.command("list")
def vterm_queue_list(
    target: str = typer.Option("http://127.0.0.1:9876", help="HTTP base URL"),
    token: str | None = typer.Option(None, help="X-VTerm-Token for auth"),
) -> None:
    import aiohttp, asyncio as _asyncio, json as _json, sys as _sys
    async def _go():
        headers = {"X-VTerm-Token": token} if token else None
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(f"{target}/queue") as r:
                _sys.stdout.write(_json.dumps({"status": r.status, **(await r.json())}) + "\n")
    _asyncio.run(_go())


@queue_app.command("wait")
def vterm_queue_wait(
    job_id: int = typer.Argument(..., help="Job id"),
    target: str = typer.Option("http://127.0.0.1:9876", help="HTTP base URL"),
    token: str | None = typer.Option(None, help="X-VTerm-Token for auth"),
    timeout: float = typer.Option(30.0, help="Max seconds to wait"),
    interval: float = typer.Option(0.25, help="Polling interval seconds"),
) -> None:
    import aiohttp, asyncio as _asyncio, json as _json, sys as _sys, time as _time
    async def _go():
        headers = {"X-VTerm-Token": token} if token else None
        t0 = _time.time()
        async with aiohttp.ClientSession(headers=headers) as s:
            while True:
                async with s.get(f"{target}/queue/{job_id}") as r:
                    data = await r.json()
                    status = data.get("status")
                    if status in {"done","error"}:
                        _sys.stdout.write(_json.dumps({"status": r.status, **data}) + "\n"); return
                if _time.time() - t0 > timeout:
                    _sys.stdout.write(_json.dumps({"error":"timeout"}) + "\n"); return
                await _asyncio.sleep(interval)
    _asyncio.run(_go())


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


@app.command("auth-check")
def auth_check(
    profile: str = typer.Option("default", help="Named profile to audit"),
    headless: bool = typer.Option(True, help="Run browser headless for verification"),
) -> None:
    """Audit cookies and verify session login in a real browser context."""
    from .cookies import load_cookies_best_effort, merge_into_storage
    cfg = Config.from_env()
    if profile:
        cfg.profile_name = profile
    # Prefer config/profiles/<profile>/storageState.json
    cfg_storage = Path("config/profiles") / cfg.profile_name / "storageState.json"
    if cfg_storage.exists():
        cfg.storage_state = cfg_storage
        cfg.user_data_dir = Path(".x-user") / cfg.profile_name
    else:
        s, u = profile_paths(cfg.profile_name)
        cfg.storage_state = s
        cfg.user_data_dir = u
    cfg.headless = headless

    cookies = load_cookies_best_effort(profile=cfg.profile_name)
    key_names = {"auth_token", "ct0", "kdt", "att"}
    present = {c.get("name") for c in cookies if isinstance(c, dict)}
    have = sorted(list(key_names & present))
    print(f"[cyan]Cookie audit:[/cyan] total={len(cookies)} keys={have}")

    # Merge cookies into storage if storage missing or empty
    try:
        need_merge = not cfg.storage_state.exists()
        if not need_merge:
            try:
                data = json.loads(cfg.storage_state.read_text())
                need_merge = not data.get("cookies")
            except Exception:
                need_merge = True
        if cookies and need_merge:
            merge_into_storage(cfg.storage_state, cookies, filter_domains=[".x.com", ".twitter.com"])
            print(f"[green]Merged cookies -> {cfg.storage_state}[/green]")
    except Exception:
        pass

    async def _run() -> None:
        async with Browser(cfg, label="auth-check") as b:
            await b.page.goto(cfg.base_url, wait_until="domcontentloaded")
            ok = await is_logged_in(b.page)
            if ok:
                print("[green]Session valid (logged in).[/green]")
            else:
                print("[yellow]Session not logged in.[/yellow]")
    asyncio.run(_run())


@session_app.command("bootstrap")
def session_bootstrap(
    headless: bool = typer.Option(False, help="Open a visible browser window for manual login"),
    persist_session: bool = typer.Option(True, help="Persist session data under the profile"),
    storage_state: str = typer.Option("auth/storageState.json", help="Storage state path"),
    user_data_dir: str = typer.Option(".x-user", help="User data dir (persistent context)"),
    proxy_url: Optional[str] = typer.Option(None, help="Proxy URL (optional)"),
    profile: str = typer.Option("default", help="Profile name (maps storage/user dirs)"),
    timeout_s: int = typer.Option(600, help="Max seconds to wait for manual login"),
):
    cfg = _cfg(headless, persist_session, storage_state, user_data_dir, proxy_url, profile)

    async def _run() -> None:
        from .flows.login import is_logged_in
        async with Browser(cfg, label="bootstrap") as b:
            print("[yellow]Opening X in a browser window. Please log in manually.[/yellow]")
            await b.page.goto(cfg.base_url, wait_until="domcontentloaded")
            import time as _time
            t0 = _time.time()
            while True:
                if await is_logged_in(b.page):
                    print(f"[green]Login detected. Session saved to {cfg.storage_state}[/green]")
                    return
                if ( _time.time() - t0 ) > timeout_s:
                    raise RuntimeError("Timeout waiting for manual login.")
                await asyncio.sleep(2.0)

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


@health_app.command("proxy")
def health_proxy_cmd(
    url: str = typer.Option("https://api.ipify.org?format=json", help="Probe URL (ipify/httpbin)")
    ,
    expect_ip: str | None = typer.Option(None, help="If set, require IP match for success")
    ,
    profile: str | None = typer.Option(None, help="Profile name to use for this check")
) -> None:
    cfg = Config.from_env()
    if profile:
        cfg.profile_name = profile
        s, u = profile_paths(profile)
        cfg.storage_state = s
        cfg.user_data_dir = u

    async def _run() -> None:
        data = await health_proxy_check(cfg, url)
        ok = True
        if expect_ip is not None:
            ok = (data.get("ip") == expect_ip)
        # write result
        record_action_result(
            "proxy_verify",
            ok,
            cfg,
            {"url": url, "expect_ip": expect_ip, "profile": cfg.profile_name},
        )
        from rich import print as rprint
        rprint({"ok": ok, **data})

    asyncio.run(_run())


@health_app.command("system")
def health_system_cmd(
    json_out: Optional[Path] = typer.Option(None, help="Path to write JSON report"),
    vterm_http_base: Optional[str] = typer.Option(None, help="Override VTerm HTTP base URL"),
) -> None:
    cfg = Config.from_env()
    report = asyncio.run(health_system(cfg, vterm_http_base=vterm_http_base))
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2))
        print(f"[green]Wrote system health report to {json_out}[/green]")
    else:
        print(json.dumps(report, indent=2))


@health_app.command("system-html")
def health_system_html_cmd(
    out_html: Path = typer.Option(Path("Docs/status/system_health.html"), help="HTML output path"),
    out_json: Optional[Path] = typer.Option(Path("Docs/status/system_health.json"), help="Optional JSON output path"),
    vterm_http_base: Optional[str] = typer.Option(None, help="Override VTerm HTTP base URL"),
) -> None:
    cfg = Config.from_env()
    report = asyncio.run(health_system(cfg, vterm_http_base=vterm_http_base))
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2))
        print(f"[green]Wrote {out_json}[/green]")
    path = write_system_health_html(report, out_html)
    print(f"[green]Wrote {path}[/green]")


@health_app.command("snapshot")
def health_snapshot_cmd(
    tweet_url: Optional[str] = typer.Option(None, help="A tweet/status URL or id to probe"),
    profile: Optional[str] = typer.Option(None, help="A profile handle or URL to probe"),
    require: str = typer.Option("compose,tweet,profile", help="Comma list of required groups: compose,tweet,profile"),
    json_out: Optional[Path] = typer.Option(None, help="Path to write JSON result"),
) -> None:
    cfg = Config.from_env()

    async def _run() -> None:
        snap = await health_selectors_snapshot(cfg, tweet_url=tweet_url, profile=profile)
        reqs = {s.strip().lower() for s in require.split(',') if s.strip()}
        ok = health_evaluate_snapshot(
            snap,
            require_compose=('compose' in reqs),
            require_tweet=('tweet' in reqs),
            require_profile=('profile' in reqs),
        )
        # record as result
        record_action_result(
            "selectors_snapshot",
            ok,
            cfg,
            {"require": list(reqs), "snapshot": snap},
        )
        from rich import print as rprint
        resp = {"ok": ok, **snap}
        if not ok:
            resp["hints"] = health_drift_hints(snap)
        rprint(resp)
        if json_out:
            import json
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json.dumps(resp, ensure_ascii=False, indent=2))

    asyncio.run(_run())


@health_app.command("checklist")
def health_checklist(
    tweet_url: Optional[str] = typer.Option(None, help="A tweet/status URL or id to probe"),
    profile: Optional[str] = typer.Option(None, help="A profile handle or URL to probe"),
    out: Path = Path("Docs/status/selectors_checklist.md"),
) -> None:
    cfg = Config.from_env()

    async def _run() -> None:
        snap = await health_selectors_snapshot(cfg, tweet_url=tweet_url, profile=profile)
        hints = health_drift_hints(snap)
        # generate markdown
        lines = []
        from datetime import datetime
        ts = datetime.now().isoformat(sep=' ', timespec='seconds')
        lines.append(f"# Selectors Checklist (Generated {ts})\n")
        lines.append("## Compose")
        c = snap.get('compose', {})
        lines.append(f"- Textbox: {c.get('textbox')} (count={c.get('textbox_count')})")
        lines.append(f"- Submit: {c.get('submit')} (count={c.get('submit_count')})\n")
        lines.append("## Tweet")
        t = snap.get('tweet', {})
        lines.append(f"- Reply: {t.get('reply')} (count={t.get('reply_count')})")
        lines.append(f"- Like: {t.get('like')} (count={t.get('like_count')})")
        lines.append(f"- Retweet: {t.get('retweet')} (count={t.get('retweet_count')})\n")
        lines.append("## Profile")
        p = snap.get('profile', {})
        lines.append(f"- Follow: {p.get('follow')} (count={p.get('follow_count')})")
        lines.append(f"- Unfollow: {p.get('unfollow')} (count={p.get('unfollow_count')})")
        lines.append(f"- Message: {p.get('message')} (count={p.get('message_count')})\n")
        if hints:
            lines.append("## Hints")
            for h in hints:
                lines.append(f"- {h}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines))
        from rich import print as rprint
        rprint({"written": str(out), "hints": hints})

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


@report_app.command("html")
def report_html_cmd(
    index: Path = Path("artifacts/results/index.jsonl"),
    out: Path = Path("artifacts/results/report.html"),
    actions: str = typer.Option("", help="Comma-separated list of actions to include (optional)"),
    limit: int = typer.Option(100, help="Max number of records"),
    date: str = typer.Option("", help="Filter by date (YYYY-MM-DD) optional"),
) -> None:
    acts = [a.strip() for a in actions.split(",") if a.strip()] if actions else None
    path = report_html(index, out, actions=acts, limit=limit, date_str=(date or None))
    print(f"[green]Wrote {path}[/green]")


@report_app.command("threshold")
def report_threshold_cmd(
    index: Path = Path("artifacts/results/index.jsonl"),
    actions: str = typer.Option("", help="Comma-separated actions filter (optional)"),
    window: int = typer.Option(100, help="Window size (last N records)"),
    min_rate: float = typer.Option(0.8, help="Minimum success rate threshold (0-1)"),
) -> None:
    acts = [a.strip() for a in actions.split(",") if a.strip()] if actions else None
    ok = report_check_threshold(index, acts, window, min_rate)
    if not ok:
        print(f"[red]Threshold check failed: window={window}, min_rate={min_rate}[/red]")
        raise typer.Exit(code=1)
    print("[green]Threshold check passed.[/green]")


@report_app.command("vterm-audit")
def report_vterm_audit(
    log: Path = Path("Docs/status/vterm_audit.jsonl"),
    out_html: Path = Path("Docs/status/vterm_audit_report.html"),
    out_json: Path | None = Path("Docs/status/vterm_audit_summary.json"),
) -> None:
    from .audit_report import write_vterm_audit_report
    summary = write_vterm_audit_report(log, out_html, out_json)
    from rich import print as rprint
    rprint({"written": str(out_html), "summary": summary})


@report_app.command("json")
def report_json_cmd(
    index: Path = Path("artifacts/results/index.jsonl"),
    actions: str = typer.Option("", help="Comma-separated actions filter (optional)"),
    window: int = typer.Option(200, help="Window size (last N records)"),
    out: Optional[Path] = typer.Option(None, help="Output JSON file (optional)"),
) -> None:
    acts = [a.strip() for a in actions.split(",") if a.strip()] if actions else None
    from .report import consolidate as report_consolidate
    data = report_consolidate(index, acts, window=window)
    from rich import print as rprint
    rprint(data)
    if out:
        import json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@results_app.command("last")
def results_last(index: Path = Path("artifacts/results/index.jsonl")) -> None:
    if not index.exists():
        print("[yellow]No index.jsonl found.[/yellow]")
        raise typer.Exit(code=0)
    lines = index.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        print("[yellow]Index is empty.[/yellow]")
        raise typer.Exit(code=0)
    import json
    data = json.loads(lines[-1])
    from rich import print as rprint
    rprint(data)


@results_app.command("tail")
def results_tail(index: Path = Path("artifacts/results/index.jsonl"), n: int = typer.Option(10, help="Lines from end"), action: str = typer.Option("", help="Filter by action")) -> None:
    if not index.exists():
        print("[yellow]No index.jsonl found.[/yellow]")
        raise typer.Exit(code=0)
    import json
    from rich import print as rprint
    lines = index.read_text(encoding="utf-8").strip().splitlines()
    sel = []
    for line in reversed(lines):
        if len(sel) >= n:
            break
        try:
            rec = json.loads(line)
            if action and str(rec.get('action','')).lower() != action.lower():
                continue
            sel.append(rec)
        except Exception:
            continue
    rprint(list(reversed(sel)))

@vtermd_app.command("start")
def vtermd_start(
    socket_path: Path = typer.Option(Path(DEFAULT_SOCKET), help="UNIX socket path"),
    init_cmd: Optional[str] = typer.Option(None, help="Initial command to write (interactive)"),
) -> None:
    d = VTermDaemon(str(socket_path), init_cmd=init_cmd)
    # Run in foreground; use a supervisor to daemonize if desired
    try:
        d.serve()
    except KeyboardInterrupt:
        pass


@vtermd_app.command("stop")
def vtermd_stop(
    socket_path: Path = typer.Option(Path(DEFAULT_SOCKET), help="UNIX socket path"),
) -> None:
    try:
        resp = client_request(str(socket_path), {"op": "shutdown"})
        print(resp)
    except Exception as e:
        print({"error": str(e)})


@vtermd_app.command("exec")
def vtermd_exec(
    socket_path: Path = typer.Option(Path(DEFAULT_SOCKET), help="UNIX socket path"),
    run: Optional[str] = typer.Option(None, help="Command to run (sentinel-wrapped)"),
    write: Optional[str] = typer.Option(None, help="Raw text to write"),
    read_timeout: float = typer.Option(0.25, help="Timeout for read op (seconds)"),
) -> None:
    if run:
        resp = client_request(str(socket_path), {"op": "run", "cmd": run})
        sys.stdout.write(json.dumps(resp) + "\n")
        return
    if write is not None:
        resp = client_request(str(socket_path), {"op": "write", "text": write})
        sys.stdout.write(json.dumps(resp) + "\n")
        return
    # default: read
    resp = client_request(str(socket_path), {"op": "read", "timeout": read_timeout})
    sys.stdout.write(json.dumps(resp) + "\n")

# attach vtermd subapp after commands are registered
app.add_typer(vtermd_app, name="vtermd", help="VTerm UNIX-socket daemon (singleton PTY)")
@app.command("reply-notmine")
def reply_notmine(
    profile: str = typer.Option("4botbsc", help="Profile name for 4bot account"),
    max_replies: int = typer.Option(50, help="Maximum replies to send"),
    headless: bool = typer.Option(True, help="Run headless"),
    x_user: Optional[str] = typer.Option(None, help="X username/email for login context"),
    x_handle: Optional[str] = typer.Option("4botbsc", help="Our handle to exclude (no @)"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ system prompt path (style only)"),
    vterm_base: Optional[str] = typer.Option(None, help="If set, use Claude via VTerm HTTP base"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm token"),
    dry_run: bool = typer.Option(False, help="If true, print plan only"),
) -> None:
    import os, asyncio
    from .profiles import profile_paths

    if x_user:
        os.environ['X_USER'] = x_user
    if x_handle:
        os.environ['X_HANDLE'] = x_handle

    cfg = Config.from_env()
    cfg.headless = headless
    # prefer config/profiles/<name>/storageState.json if present
    cfg_storage = Path("config/profiles") / profile / "storageState.json"
    if cfg_storage.exists():
        cfg.storage_state = cfg_storage
        cfg.user_data_dir = Path(".x-user") / profile
    else:
        s, u = profile_paths(profile)
        cfg.storage_state = s
        cfg.user_data_dir = u

    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    claude = None
    if vterm_base:
        claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode="run-pipe")

    async def _collect_targets(page) -> list[dict]:
        targets: list[dict] = []
        seen: set[str] = set()
        our = (cfg.handle or x_handle or "").lstrip('@').lower()
        # Check mentions first, then notifications
        for path in ("/notifications/mentions", "/notifications"):
            try:
                await page.goto(cfg.base_url + path, wait_until="domcontentloaded")
            except Exception:
                continue
            for _ in range(12):  # ~12 screens
                items = await page.evaluate(
                    r"""
                    () => {
                      const out = [];
                      for (const a of document.querySelectorAll('article')) {
                        const link = a.querySelector("a[href*='/status/']");
                        if (!link) continue;
                        const href = link.href || link.getAttribute('href') || '';
                        const idm = href.match(/status\/(\d+)/);
                        const id = idm ? idm[1] : null;
                        const authorA = a.querySelector("[data-testid='User-Name'] a[href^='/']");
                        const handle = authorA ? (authorA.getAttribute('href') || '').replace(/^\//,'') : '';
                        const textEl = a.querySelector("[data-testid='tweetText']");
                        const content = textEl ? textEl.textContent : '';
                        if (id) out.push({id, url: href.startsWith('http')?href:('https://x.com' + href), handle, content});
                      }
                      return out;
                    }
                    """
                )
                for it in items:
                    hid = str(it.get('id', ''))
                    h = str(it.get('handle','')).lower()
                    if not hid or hid in seen:
                        continue
                    if our and h == our:
                        continue
                    seen.add(hid); targets.append(it)
                # scroll
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await asyncio.sleep(1.0)
            if len(targets) >= max_replies:
                break
        return targets[:max_replies]

    def _simple_cz_reply(content: str) -> str:
        base = "4. BUIDL > FUD. Long-term > noise."
        # tiny heuristic tweak
        cl = (content or '').lower()
        hint = (
            " Welcome clear rules; collaborate, protect users." if any(k in cl for k in ("sec","reg","doj","ban","illegal","fine")) else
            " Focus on real builders; avoid rumors." if any(k in cl for k in ("scam","rug","ponzi")) else
            " Transparency, fix fast, users first." if any(k in cl for k in ("hack","exploit","breach","drain")) else
            " Zoom out. Tech adoption compounds." if any(k in cl for k in ("dead","zero","collapse","insolvent")) else
            " Keep users #SAFU."
        )
        txt = f"{base}{hint} — CZ-inspired"
        return txt[:240]

    async def _run():
        if claude:
            await claude.ensure_ready()
        from .browser import Browser
        from .flows.login import login_if_needed
        bot = XBot(cfg)
        async with Browser(cfg, label="reply_notmine") as b:
            await login_if_needed(b.page, cfg)
            targets = await _collect_targets(b.page)
            if not targets:
                print("[yellow]No target posts found (not from our handle).[/yellow]")
                return
            for i, t in enumerate(targets, 1):
                url = t.get('url') or ''
                content = t.get('content') or ''
                if claude:
                    from dataclasses import dataclass
                    from datetime import datetime as _dt
                    @dataclass
                    class _P:
                        author: str = ''
                        author_handle: str = cfg.handle or (x_handle or '')
                        content: str = f"Reply as CZ (style only, non-impersonating). Keep under 240 chars. Context: {content}"
                        timestamp: _dt = _dt.now()
                    text = await claude.reply(_P())
                    text = (text or _simple_cz_reply(content)).strip()
                else:
                    text = _simple_cz_reply(content)
                print(f"[cyan]{i}/{len(targets)} Replying to {url}:\n  -> {text}")
                if not dry_run:
                    await bot.reply(url, text)

    asyncio.run(_run())
@app.command("auto-reply")
def auto_reply(
    profile: str = typer.Option("4botbsc", help="Profile name to use for session"),
    vterm_base: str = typer.Option("http://127.0.0.1:9876", help="VTerm HTTP base URL"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm HTTP token (if configured)"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ persona system prompt path"),
) -> None:
    """Launch a headless, in-memory daemon that replies to posts not from our handle as CZ."""
    from .auto_responder import run as arun
    arun(profile=profile, vterm_base=vterm_base, vterm_token=vterm_token, system_path=str(system_path), vterm_mode="run-pipe")

@app.command("reply-from-list")
def reply_from_list(
    list_path: Path = typer.Option(Path("Docs/4Bot Tweets.md"), help="Markdown with tweet URLs"),
    profile: str = typer.Option("4botbsc", help="Profile/session name"),
    headless: bool = typer.Option(True, help="Run headless"),
    x_user: Optional[str] = typer.Option(None, help="X username/email"),
    x_handle: Optional[str] = typer.Option("4botbsc", help="Our handle (exclude author check)"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ system prompt path (style only)"),
    vterm_base: Optional[str] = typer.Option(None, help="Claude VTerm HTTP base (optional)"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm token"),
    max_replies: int = typer.Option(200, help="Cap number of replies"),
    dry_run: bool = typer.Option(False, help="Do not post; print only"),
) -> None:
    import os, re, asyncio
    from .profiles import profile_paths

    if x_user:
        os.environ['X_USER'] = x_user
    if x_handle:
        os.environ['X_HANDLE'] = x_handle

    cfg = Config.from_env()
    cfg.headless = headless
    # prefer config/profiles/<name>/storageState.json
    cfg_storage = Path("config/profiles") / profile / "storageState.json"
    if cfg_storage.exists():
        cfg.storage_state = cfg_storage
        cfg.user_data_dir = Path(".x-user") / profile
    else:
        s, u = profile_paths(profile)
        cfg.storage_state = s
        cfg.user_data_dir = u

    text = list_path.read_text(encoding="utf-8")
    urls = re.findall(r"\[[^\]]+\]\((https?://x\.com/[^)]+)\)", text) + re.findall(r"(?<!\()\bhttps?://x\.com/[^\s)]+", text)
    urls = [u.strip().rstrip(").,;") for u in urls]
    seen = set(); dedup = []
    for u in urls:
        if u not in seen:
            seen.add(u); dedup.append(u)
    dedup = dedup[:max_replies]

    system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
    claude = None
    if vterm_base:
        claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode="run-pipe")

    def _simple_cz_reply(content: str) -> str:
        base = "4. BUIDL > FUD. Long-term > noise."
        cl = (content or '').lower()
        hint = (
            " Welcome clear rules; collaborate, protect users." if any(k in cl for k in ("sec","reg","doj","ban","illegal","fine")) else
            " Focus on real builders; avoid rumors." if any(k in cl for k in ("scam","rug","ponzi")) else
            " Transparency, fix fast, users first." if any(k in cl for k in ("hack","exploit","breach","drain")) else
            " Zoom out. Tech adoption compounds." if any(k in cl for k in ("dead","zero","collapse","insolvent")) else
            " Keep users #SAFU."
        )
        txt = f"{base}{hint} — CZ-inspired"
        return txt[:240]

    async def _run():
        if claude:
            await claude.ensure_ready()
        from .browser import Browser
        from .flows.login import login_if_needed
        bot = XBot(cfg)
        async with Browser(cfg, label="reply_from_list") as b:
            await login_if_needed(b.page, cfg)
            for i, url in enumerate(dedup, 1):
                content_hint = f"Reply as CZ (style only). Keep under 240 chars."
                text = None
                if claude:
                    from dataclasses import dataclass
                    from datetime import datetime as _dt
                    @dataclass
                    class _P:
                        author: str = ''
                        author_handle: str = cfg.handle or (x_handle or '')
                        content: str = content_hint
                        timestamp: _dt = _dt.now()
                    text = await claude.reply(_P())
                if not text:
                    text = _simple_cz_reply("")
                print(f"[cyan]{i}/{len(dedup)} Replying to {url}:\n  -> {text}")
                if not dry_run:
                    await bot.reply(url, text)

    asyncio.run(_run())
@app.command("reply-from-file")
def reply_from_file(
    profile: str = typer.Option("4botbsc", help="Profile to use for session"),
    list_path: Path = typer.Option(Path("Docs/4Bot Tweets.md"), help="Markdown or text file with one or more X status URLs"),
    headless: bool = typer.Option(True, help="Run headless (in-memory; does not persist session)"),
    vterm_base: Optional[str] = typer.Option(None, help="Optional VTerm HTTP base for Claude CZ style"),
    vterm_token: Optional[str] = typer.Option(None, help="VTerm HTTP token"),
    system_path: Path = typer.Option(Path("CLAUDE.md"), help="CZ persona system prompt path"),
    x_user: Optional[str] = typer.Option(None, help="X username/email"),
    x_handle: Optional[str] = typer.Option("4botbsc", help="Our handle (no @)"),
    dry_run: bool = typer.Option(False, help="Print plan only; do not post"),
) -> None:
    import re, asyncio
    if x_user:
        import os as _os
        _os.environ['X_USER'] = x_user
    if x_handle:
        import os as _os
        _os.environ['X_HANDLE'] = x_handle
    cfg = Config.from_env()
    cfg.headless = bool(headless)
    # Prefer using the existing on-disk profile for a logged-in session (headless-persistent)
    cfg.persist_session = True
    # Prefer config/profiles/<name>/storageState.json when present
    cfg_storage = Path("config/profiles") / profile / "storageState.json"
    if cfg_storage.exists():
        cfg.storage_state = cfg_storage
        cfg.user_data_dir = Path(".x-user") / profile
    else:
        s, u = profile_paths(profile)
        cfg.storage_state = s
        cfg.user_data_dir = u
    # Provide a stable desktop UA if none set
    if not cfg.user_agent:
        cfg.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    # Load optional Claude
    claude = None
    if vterm_base:
        system_prompt = system_path.read_text(encoding="utf-8") if system_path.exists() else ""
        claude = ClaudeGen(base=vterm_base, token=vterm_token, system_prompt=system_prompt, mode="run-pipe")

    text = list_path.read_text(encoding="utf-8")
    urls = re.findall(r"https?://x\.com/[^\s\)\]\}]+", text)
    urls = [u.rstrip(').,;*]') for u in urls]
    # de-dup preserve order
    seen = set(); dedup = []
    for u in urls:
        if u not in seen:
            seen.add(u); dedup.append(u)

    def _simple_cz_reply(content: str) -> str:
        base = "4. Ignore FUD. BUIDL. Long-term > noise."
        cl = (content or '').lower()
        hint = (
            " Clear rules help builders. #SAFU" if any(k in cl for k in ("reg","sec","policy","law")) else
            " Focus on shipping real utility." if any(k in cl for k in ("scam","rug","ponzi")) else
            " Resilience wins over cycles." if any(k in cl for k in ("dump","crash","bear","dead")) else
            " Users first. Transparency matters."
        )
        return (f"{base} {hint} — CZ-inspired")[:240]

    async def _run():
        if claude:
            try:
                await claude.ensure_ready()
            except Exception:
                pass
        bot = XBot(cfg)
        # Proactively open a page to trigger cookie/session load
        from .browser import Browser
        from .flows.login import login_if_needed
        async with Browser(cfg, label="reply_from_file") as b:
            try:
                await login_if_needed(b.page, cfg)
            except Exception:
                pass
            for i, url in enumerate(dedup, 1):
                content_hint = f"Reply in CZ persona (style only, non-impersonating). Keep under 240 chars. URL: {url}"
                if claude:
                    from dataclasses import dataclass
                    from datetime import datetime as _dt
                    @dataclass
                    class _P:
                        author: str = ''
                        author_handle: str = cfg.handle or (x_handle or '')
                        content: str = content_hint
                        timestamp: _dt = _dt.now()
                    text = (await claude.reply(_P())) or _simple_cz_reply(content_hint)
                else:
                    text = _simple_cz_reply(content_hint)
                text = text.strip()[:280]
                print(f"[{i}/{len(dedup)}] Replying to {url}: {text}")
                if not dry_run:
                    try:
                        await bot.reply(url, text)
                    except Exception as e:
                        print({"error": str(e), "url": url})

    asyncio.run(_run())

if __name__ == "__main__":
    app()
