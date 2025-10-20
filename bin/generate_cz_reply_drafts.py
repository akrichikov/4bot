from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from xbot.config import Config

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs"
STATUS_DIR = DOCS / "status"
TWEETS_MD = DOCS / "4Bot Tweets.md"


def extract_x_urls(text: str) -> List[str]:
    urls: List[str] = []
    # 1) markdown links: [label](https://x.com/...)
    urls += re.findall(r"\[[^\]]+\]\((https?://x\.com/[^)]+)\)", text)
    # 2) bare links
    urls += re.findall(r"(?<!\()\bhttps?://x\.com/[^\s)]+", text)
    # normalize
    cleaned = [u.strip().rstrip(").,;\n\r") for u in urls]
    # de-dup preserve order
    seen = set()
    out: List[str] = []
    for u in cleaned:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def cz_style_reply_generic(context_hint: str | None = None) -> str:
    parts: List[str] = []
    parts.append("4.")
    if context_hint:
        parts.append(context_hint)
    parts.append("BUIDL > FUD. Long-term > noise.")
    parts.append("Stay focused, keep users #SAFU.")
    parts.append("— CZ-inspired")
    # keep under ~240 characters
    text = " ".join(parts)
    return text[:238]


def generate_replies(urls: List[str]) -> Dict[str, str]:
    replies: Dict[str, str] = {}
    for u in urls:
        # Very light heuristic buckets (without fetching tweet content)
        hint: str | None = None
        lu = u.lower()
        if any(k in lu for k in ["hack", "exploit", "drain", "breach"]):
            hint = "Transparency, fix fast, users first."
        elif any(k in lu for k in ["scam", "rug", "ponzi"]):
            hint = "Verify sources, avoid rumors, focus on real builders."
        elif any(k in lu for k in ["dead", "zero", "collapse", "insolvent"]):
            hint = "Zoom out. Tech adoption compounds over cycles."
        elif any(k in lu for k in ["reg", "sec", "doj", "ban", "illegal", "fine"]):
            hint = "Welcome clear rules; collaborate, protect users, keep building."
        replies[u] = cz_style_reply_generic(hint)
    return replies


def main() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    if not TWEETS_MD.exists():
        raise SystemExit(f"Missing file: {TWEETS_MD}")
    text = TWEETS_MD.read_text(encoding="utf-8")
    urls = extract_x_urls(text)
    replies = generate_replies(urls)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    md_path = STATUS_DIR / f"{datetime.now().date()}_cz_reply_drafts.md"
    cfg = Config.from_env()
    outdir = cfg.report_html_outdir
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / f"cz_reply_drafts_{ts}.json"

    lines: List[str] = []
    lines.append("# CZ-Style Reply Drafts (Non-Impersonating)")
    lines.append("")
    lines.append("- Source: Docs/4Bot Tweets.md")
    lines.append("- Persona: prompts/persona_cz.system.md (style only; not identity)")
    lines.append("- Disclaimer: Replies are CZ-inspired and do not claim to be CZ.")
    lines.append("")
    for i, (u, r) in enumerate(replies.items(), 1):
        lines.append(f"{i}. {u}")
        lines.append(f"   - Draft: {r}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_path.write_text(json.dumps({"urls": urls, "replies": replies}, indent=2), encoding="utf-8")
    print(str(md_path))


if __name__ == "__main__":
    main()
