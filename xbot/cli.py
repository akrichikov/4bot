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
from .health import selectors_snapshot as health_selectors_snapshot, evaluate_snapshot as health_evaluate_snapshot, drift_hints as health_drift_hints
from .results import record_action_result
from .scheduler import run_schedule
from .report import summary as report_summary, export_csv as report_export_csv, check_threshold as report_check_threshold
from .report_html import html_report as report_html
from .profiles import profile_paths, list_profiles, ensure_profile_dirs, clear_state, set_overlay_value, del_overlay_key, read_overlay
from .vterm import VTerm
from .vtermd import VTermDaemon, client_request, DEFAULT_SOCKET
from .vterm_http import VTermHTTPServer
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
) -> None:
    server = VTermHTTPServer(host=host, port=port, token=token, rate_qps=rate_qps, rate_burst=rate_burst, audit_log=audit_log, audit_enabled=audit)
    server.run()


@vterm_app.command("client")
def vterm_client(
    mode: str = typer.Argument("http", help="http|unix"),
    target: str = typer.Option("http://127.0.0.1:9876", help="Base URL (http) or socket path (unix)"),
    token: str | None = typer.Option(None, help="Token for HTTP mode"),
    run: str | None = typer.Option(None, help="Command to run"),
    write: str | None = typer.Option(None, help="Text to write"),
    read_timeout: float = typer.Option(0.25, help="Read timeout"),
) -> None:
    from .vterm_client import VTermClient
    import asyncio as _asyncio

    if mode == "http":
        client = VTermClient(mode="http", base=target, token=token)
        async def _go():
            import sys as _sys, json as _json
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

if __name__ == "__main__":
    app()
