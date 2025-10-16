from __future__ import annotations

from pathlib import Path
import json
import sys


def parse_netscape(lines: list[str]):
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 7:
            continue
        domain, flag, path, secure, expires, name, value = parts[:7]
        try:
            exp = int(expires)
        except Exception:
            exp = -1
        out.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": path or "/",
            "expires": exp,
            "httpOnly": False,
            "secure": (secure.upper() == 'TRUE'),
            "sameSite": "Lax",
        })
    return out


def main():
    if len(sys.argv) < 3:
        print("usage: convert_netscape_to_json.py <in.txt> <out.json>")
        sys.exit(2)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    cookies = parse_netscape(src.read_text(encoding='utf-8', errors='ignore').splitlines())
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
    print(dst)


if __name__ == '__main__':
    main()

