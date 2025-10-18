from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import itertools


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
    if "sameSite" in c or "same_site" in c:
        same_site = c.get("sameSite", c.get("same_site"))
    else:
        same_site = "Lax"
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


def _variants_for_x(dom: str) -> List[str]:
    v = [dom]
    if "twitter.com" in dom and "x.com" not in dom:
        v.append(dom.replace("twitter.com", "x.com"))
    if dom.startswith(".") and not dom.endswith("x.com"):
        v.append(".x.com")
    return list(dict.fromkeys(v))


def load_cookies_best_effort(profile: str = "4botbsc") -> List[Cookie]:
    """Load cookies from best available sources for a profile.

    Order of precedence:
      1) auth_data/x_cookies.json (netscape/chrome export)
      2) chrome_profiles/cookies/default_cookies.json (project export)
      3) config/profiles/<profile>/storageState.json (playwright state) – treated as cookie source
      4) auth/<profile>/storageState.json (legacy state) – treated as cookie source
    """
    candidates = [
        Path("auth_data/x_cookies.json"),
        Path("chrome_profiles/cookies/default_cookies.json"),
        Path("config/profiles") / profile / "storageState.json",
        Path("auth") / profile / "storageState.json",
    ]
    cookies: List[Cookie] = []
    for p in candidates:
        try:
            if p.exists():
                cookies.extend(load_cookie_json(p))
        except Exception:
            continue
    # Add x.com variants for twitter.com
    out: Dict[Tuple[str, str, str], Cookie] = {}
    for c in cookies:
        dom = c.get("domain", "")
        for d in _variants_for_x(dom):
            cc = dict(c); cc["domain"] = d
            out[_ckey(cc)] = cc
    return list(out.values())
