from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


Cookie = Dict[str, Any]


def _normalize_cookie(c: Dict[str, Any]) -> Cookie:
    name = c.get("name")
    value = c.get("value")
    domain = c.get("domain")
    path = c.get("path", "/")
    if not (name and value and domain):
        raise ValueError("invalid cookie: missing name/value/domain")
    # expires normalization
    expires = c.get("expires")
    if expires is None and "expirationDate" in c:
        # chrome export uses seconds float
        try:
            expires = int(float(c["expirationDate"]))
        except Exception:
            expires = -1
    http_only = bool(c.get("httpOnly", c.get("httponly", False)))
    secure = bool(c.get("secure", False))
    same_site = c.get("sameSite") or c.get("same_site") or "Lax"
    if isinstance(same_site, str):
        s = same_site.lower()
        if s.startswith("lax"):
            same_site = "Lax"
        elif s.startswith("str"):
            same_site = "Strict"
        else:
            same_site = "None"
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": path,
        "expires": expires if expires is not None else -1,
        "httpOnly": http_only,
        "secure": secure,
        "sameSite": same_site,
    }


def load_cookie_json(path: Path) -> List[Cookie]:
    data = json.loads(path.read_text())
    cookies: List[Cookie] = []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        if "cookies" in data and isinstance(data["cookies"], list):
            raw = data["cookies"]
        elif "origins" in data:
            raw = []
        else:
            raw = []
    else:
        raw = []

    for c in raw:
        try:
            cookies.append(_normalize_cookie(c))
        except Exception:
            continue
    return cookies


def _ckey(c: Cookie) -> Tuple[str, str, str]:
    return (c.get("name", ""), c.get("domain", ""), c.get("path", "/"))


def merge_into_storage(storage_path: Path, new_cookies: Iterable[Cookie], filter_domains: Iterable[str] | None = None) -> int:
    storage = {"cookies": [], "origins": []}  # playwright storageState-like
    if storage_path.exists():
        try:
            storage = json.loads(storage_path.read_text())
        except Exception:
            pass
    existing = { _ckey(c): c for c in storage.get("cookies", []) }
    count = 0
    for c in new_cookies:
        if filter_domains:
            dom = c.get("domain", "")
            if not any(dom.endswith(d) or dom == d for d in filter_domains):
                continue
        k = _ckey(c)
        existing[k] = c
        count += 1
    storage["cookies"] = list(existing.values())
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(json.dumps(storage, ensure_ascii=False, indent=2))
    return count

