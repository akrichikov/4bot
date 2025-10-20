#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
from pathlib import Path
from string import Template
from typing import Dict, List, Tuple

import typer
from rich import print


app = typer.Typer(add_completion=False, no_args_is_help=True)


def _default_vars(repo_root: Path) -> Dict[str, str]:
    return {
        "REPO_ROOT": str(repo_root),
        "LOG_DIR": str(repo_root / "logs"),
        "X_USER": os.getenv("X_USER", ""),
    }


def _parse_kv(overrides: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for kv in overrides:
        if "=" not in kv:
            raise typer.BadParameter(f"Invalid --var entry (expected KEY=VALUE): {kv}")
        k, v = kv.split("=", 1)
        out[k.strip()] = v
    return out


def _render_one(src: Path, dst: Path, mapping: Dict[str, str]) -> None:
    text = src.read_text(encoding="utf-8")
    rendered = Template(text).safe_substitute(mapping)
    # Avoid hard-coded absolute user home prefixes in rendered content
    if (os.sep + "Users" + os.sep) in rendered:
        raise RuntimeError(f"Absolute user-home path found in rendered plist: {src.name}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(rendered, encoding="utf-8")


@app.command()
def render(
    templates_dir: Path = typer.Option(Path("Docs/launchd"), help="Directory with *.template.plist"),
    out_dir: Path = typer.Option(Path("bin/launchd"), help="Output directory for rendered *.plist"),
    var: List[str] = typer.Option([], "--var", help="Override variables as KEY=VALUE (repeatable)"),
    dry_run: bool = typer.Option(False, help="Only validate and show targets; no writes"),
) -> None:
    repo_root = Path.cwd()
    mapping = _default_vars(repo_root)
    mapping.update(_parse_kv(var))

    tpls = sorted(templates_dir.glob("*.template.plist"))
    if not tpls:
        raise typer.Exit(code=1)
    for t in tpls:
        out = out_dir / t.name.replace(".template.plist", ".plist")
        print(f"[cyan]Render[/cyan] {t} -> {out}")
        if not dry_run:
            _render_one(t, out, mapping)
    print("[green]Done.[/green]")


@app.command()
def install(
    out_dir: Path = typer.Option(Path("bin/launchd"), help="Directory with rendered *.plist"),
    unload_first: bool = typer.Option(True, help="Unload existing before load"),
) -> None:
    agents = Path.home() / "Library/LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    for p in sorted(out_dir.glob("*.plist")):
        target = agents / p.name
        print(f"[cyan]Install[/cyan] {p} -> {target}")
        shutil.copy2(p, target)
        label = target.stem
        try:
            if unload_first:
                os.system(f"launchctl unload {target} >/dev/null 2>&1 || true")
        except Exception:
            pass
        os.system(f"launchctl load {target}")
    print("[green]Installed.[/green]")


if __name__ == "__main__":
    app()
