from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Any, Tuple


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
_URL_RE = re.compile(r"https?://[^\s]+", re.I)
_PROFANITY = {
    "idiot", "stupid", "dumb", "moron", "retard", "kill", "hate",
}
_ALLOWED_DOMAINS = {"x.com", "twitter.com"}


@dataclass
class RiskReport:
    pii_email: bool = False
    pii_phone: bool = False
    profanity: bool = False
    off_brand_shouting: bool = False
    excessive_emojis: bool = False
    link_block: bool = False


def analyze(text: str, ctx: Dict[str, Any] | None = None) -> RiskReport:
    t = (text or "")
    report = RiskReport()
    report.pii_email = bool(_EMAIL_RE.search(t))
    report.pii_phone = bool(_PHONE_RE.search(t))
    report.profanity = any(w in t.lower() for w in _PROFANITY)
    # shouting: >70% alphabetical uppercase and length>=8
    letters = [c for c in t if c.isalpha()]
    if letters:
        up = sum(1 for c in letters if c.isupper())
        ratio = up / max(1, len(letters))
        report.off_brand_shouting = ratio > 0.7 and len(letters) >= 8
    # emojis: naive count of typical emojis
    emojis = re.findall(r"[\U0001F300-\U0001FAFF]", t)
    report.excessive_emojis = len(emojis) > 3
    # links: block links to domains outside allowlist
    urls = _URL_RE.findall(t)
    bad_links = []
    for u in urls:
        host = re.sub(r"^https?://", "", u).split("/")[0].lower()
        if not any(host == d or host.endswith("." + d) for d in _ALLOWED_DOMAINS):
            bad_links.append(u)
    report.link_block = bool(bad_links)
    return report


def guardrail(text: str, ctx: Dict[str, Any] | None = None) -> Tuple[str, str]:
    """Apply guardrails to text.
    Returns (decision, output_text) where decision is 'PASS'|'EDIT'|'BLOCK'.
    """
    rep = analyze(text, ctx)
    if rep.profanity or rep.link_block:
        return "BLOCK", ""

    edited = text
    changed = False
    # redact PII
    if rep.pii_email:
        edited = _EMAIL_RE.sub("[redacted@email]", edited); changed = True
    if rep.pii_phone:
        edited = _PHONE_RE.sub("[redacted-phone]", edited); changed = True
    if rep.off_brand_shouting:
        edited = edited.capitalize(); changed = True
    if rep.excessive_emojis:
        edited = re.sub(r"([\U0001F300-\U0001FAFF]){4,}", "", edited); changed = True

    return ("EDIT", edited) if changed else ("PASS", text)


def evaluate_list(lines: list[str]) -> Dict[str, Any]:
    """Evaluate a list of candidate replies and summarize guardrail decisions."""
    totals = {"PASS": 0, "EDIT": 0, "BLOCK": 0}
    details = []
    for i, line in enumerate(lines):
        d, out = guardrail(line or "")
        totals[d] = totals.get(d, 0) + 1
        details.append({"index": i, "input": line, "decision": d, "output": out})
    return {"summary": totals, "items": details}
