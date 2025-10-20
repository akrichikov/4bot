#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS_DIR = ROOT / "Docs" / "status"

SCAN_PATTERN = re.compile(
    r"\b(import\s+pty\b|pty\.openpty\(|termios\b|\btty\b|TIOCSWINSZ|"
    r"class\s+VTerm\b|class\s+VTermHTTPServer\b|class\s+VTermDaemon\b|"
    r"def\s+client_request\(|DEFAULT_SOCKET\s*=|vterm_console\.|/static/vterm_console)"
)

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", ".pytest_cache", "node_modules", "dist", "build"}


def have(cmd: str) -> bool:
    return subprocess.call(["bash", "-lc", f"command -v {cmd} >/dev/null 2>&1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def run(cmd: str) -> str:
    p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return p.stdout.strip()


def tree_listing(path: Path, depth: int = 2) -> str:
    if have("tree"):
        return run(f"cd '{path}' && tree -a -I '.git|.venv|__pycache__|.pytest_cache|node_modules|dist|build|*.egg-info' -n -L {depth}")
    # fallback: simple walk
    lines: list[str] = []
    base_depth = len(path.resolve().parts)
    for root, dirs, files in os.walk(path):
        rp = Path(root)
        rel = rp.relative_to(path)
        d = len(rp.parts) - base_depth
        if d > depth:
            continue
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        indent = "  " * d
        if rel != Path('.'):
            lines.append(f"{indent}{rel}")
        for f in sorted(files)[:20]:
            lines.append(f"{indent}  {f}")
    return "\n".join(lines)


def scan_repo() -> list[str]:
    matches: list[str] = []
    # Prefer ripgrep if present
    if have("rg"):
        cmd = (
            "rg -n --hidden -S "
            "\"\\b(import\\s+pty\\b|pty\\.openpty\\(|termios\\b|\\btty\\b|TIOCSWINSZ|"
            "class\\s+VTerm\\b|class\\s+VTermHTTPServer\\b|class\\s+VTermDaemon\\b|"
            "def\\s+client_request\\(|DEFAULT_SOCKET\\s*=|vterm_console\\.|/static/vterm_console)\" "
            "--glob '!**/.git/**' --glob '!**/__pycache__/**' --glob '!**/.venv/**' --glob '!submodules/**'"
        )
        out = run(f"cd '{ROOT}' && {cmd}")
        if out:
            matches = [line.strip() for line in out.splitlines() if line.strip()]
        return matches
    # Fallback: python walk
    for rp, _, files in os.walk(ROOT):
        pr = Path(rp)
        rel = pr.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts) or str(rel).startswith('submodules'):
            continue
        for fn in files:
            if fn.endswith(('.py', '.md', '.html', '.js')):
                try:
                    text = (pr / fn).read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    continue
                for m in SCAN_PATTERN.finditer(text):
                    matches.append(f"{rel}/{fn}:{m.group(0)[:60]}")
    return matches


def provenance() -> dict[str, str]:
    code = (
        "from xbot.vterm import VTerm\n"
        "from xbot.vterm_http import VTermHTTPServer\n"
        "from xbot.vtermd import client_request\n"
        "print('VTerm', VTerm.__module__)\n"
        "print('HTTP', VTermHTTPServer.__module__)\n"
        "print('CLIENT', client_request.__module__)\n"
    )
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    out = p.stdout.strip().splitlines()
    prov = {}
    for line in out:
        if line.startswith('VTerm '):
            prov['VTerm'] = line.split(' ', 1)[1]
        elif line.startswith('HTTP '):
            prov['VTermHTTPServer'] = line.split(' ', 1)[1]
        elif line.startswith('CLIENT '):
            prov['client_request'] = line.split(' ', 1)[1]
    return prov


def write_status(note: str) -> Path:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    path = STATUS_DIR / f"pty_verify_{ts}.md"
    path.write_text(note, encoding='utf-8')
    return path


def run_once() -> Path:
    now = dt.datetime.now().isoformat(timespec='seconds')
    triad_root = tree_listing(ROOT, 2)
    triad_xbot = tree_listing(ROOT / 'xbot', 1)
    triad_apps = tree_listing(ROOT / 'apps', 1)
    triad_scripts = tree_listing(ROOT / 'scripts', 1)
    triad_tests = tree_listing(ROOT / 'tests', 1)
    matches = scan_repo()
    prov = provenance()
    ok = (
        not matches and prov.get('VTerm','').startswith('ptyterm')
        and prov.get('VTermHTTPServer','').startswith('ptyterm')
        and prov.get('client_request','').startswith('ptyterm')
    )
    note = (
        f"# PTY Verification — {now}\n\n"
        f"Result: {'CLEAN' if ok else 'ISSUES FOUND'}\n\n"
        f"## Provenance\n{prov}\n\n"
        f"## Matches (excluding submodules)\n" + ("(none)\n" if not matches else "\n".join(matches) + "\n") +
        f"\n## Root tree (depth 2)\n\n````\n{triad_root}\n````\n\n"
        f"## xbot tree\n\n````\n{triad_xbot}\n````\n\n"
        f"## apps tree\n\n````\n{triad_apps}\n````\n\n"
        f"## scripts tree\n\n````\n{triad_scripts}\n````\n\n"
        f"## tests tree\n\n````\n{triad_tests}\n````\n"
    )
    return write_status(note)


def main() -> None:
    ap = argparse.ArgumentParser(description="Continuously verify PTY implementation is externalized")
    ap.add_argument('--interval', type=float, default=0.0, help='Seconds between runs (0 = run once)')
    args = ap.parse_args()
    if args.interval <= 0:
        p = run_once()
        print(p)
        return
    try:
        import time
        while True:
            p = run_once()
            print(p)
            time.sleep(max(1.0, float(args.interval)))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

