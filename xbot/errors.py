from __future__ import annotations

from typing import Dict


def classify_exception(e: Exception) -> Dict[str, str]:
    name = type(e).__name__
    msg = str(e)
    cat = "unknown"
    if "Timeout" in name or "timeout" in msg.lower():
        cat = "timeout"
    elif "Selector" in name or "locator" in msg.lower():
        cat = "selector"
    elif "Network" in name or "net::" in msg or "ERR_" in msg:
        cat = "network"
    elif "auth" in msg.lower() or "login" in msg.lower():
        cat = "auth"
    elif "captcha" in msg.lower() or "challenge" in msg.lower():
        cat = "challenge"
    return {"category": cat, "name": name, "message": msg[:500]}

