from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Any
import json


def profile_paths(profile: str) -> Tuple[Path, Path]:
    if not profile or profile == "default":
        return Path("auth/storageState.json"), Path(".x-user")
    return Path(f"auth/{profile}/storageState.json"), Path(f".x-user/{profile}")


def list_profiles() -> List[str]:
    names = set()
    # from auth
    auth = Path("auth")
    if auth.exists():
        for p in auth.iterdir():
            if p.is_dir():
                names.add(p.name)
    # from .x-user
    xuser = Path(".x-user")
    if xuser.exists():
        for p in xuser.iterdir():
            if p.is_dir():
                names.add(p.name)
    # include default if base files exist
    if Path("auth/storageState.json").exists() or Path(".x-user").exists():
        names.add("default")
    return sorted(names)


def ensure_profile_dirs(profile: str) -> Tuple[Path, Path]:
    storage, udir = profile_paths(profile)
    storage.parent.mkdir(parents=True, exist_ok=True)
    udir.mkdir(parents=True, exist_ok=True)
    return storage, udir


def clear_state(profile: str) -> bool:
    storage, _ = profile_paths(profile)
    if storage.exists():
        storage.unlink()
        return True
    return False


def overlay_path(profile: str) -> Path:
    return Path("config/profiles") / f"{profile}.json"


def read_overlay(profile: str) -> Dict[str, Any]:
    p = overlay_path(profile)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def write_overlay(profile: str, data: Dict[str, Any]) -> None:
    p = overlay_path(profile)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def set_overlay_value(profile: str, key: str, value: Any) -> None:
    data = read_overlay(profile)
    data[key] = value
    write_overlay(profile, data)


def del_overlay_key(profile: str, key: str) -> bool:
    data = read_overlay(profile)
    if key in data:
        del data[key]
        write_overlay(profile, data)
        return True
    return False


# New helper APIs for path and profile hygiene

def storage_state_path(profile: str, prefer_config_dir: bool = True) -> Path:
    """Return preferred storageState.json path for a profile.

    Precedence (when prefer_config_dir=True):
      - config/profiles/<profile>/storageState.json
      - auth/<profile>/storageState.json (legacy)
      - auth/storageState.json (default profile)
    """
    if not profile or profile == "default":
        # default profile still can use config/profiles/default
        if prefer_config_dir:
            p = Path("config/profiles/default/storageState.json")
            if p.exists():
                return p
        return Path("auth/storageState.json")
    if prefer_config_dir:
        p = Path("config/profiles") / profile / "storageState.json"
        if p.exists():
            return p
    return Path("auth") / profile / "storageState.json"


def user_data_dir(profile: str, prefer_dot: bool = True) -> Path:
    """Return user data dir for Playwright persistent contexts.

    For the default profile: `.x-user`
    For named profile: `.x-user/<profile>`
    """
    if not profile or profile == "default":
        return Path(".x-user")
    return Path(".x-user") / profile


def cookie_candidates(profile: str) -> List[Path]:
    """Return likely cookie/storage files for best-effort cookie loading."""
    return [
        Path("auth_data/x_cookies.json"),
        Path("chrome_profiles/cookies/default_cookies.json"),
        Path("config/profiles") / profile / "storageState.json",
        Path("auth") / profile / "storageState.json",
    ]


def validate(profile: str) -> Dict[str, Any]:
    """Validate profile paths and provide quick hints/flags."""
    s = storage_state_path(profile)
    u = user_data_dir(profile)
    exists = s.exists()
    cookie_count = 0
    err = None
    if exists:
        try:
            data = json.loads(s.read_text())
            cookie_count = len(data.get("cookies", []))
        except Exception as e:
            err = str(e)
    present_candidates = [str(p) for p in cookie_candidates(profile) if p.exists()]
    return {
        "profile": profile or "default",
        "storage_state": str(s),
        "storage_exists": exists,
        "cookie_count": cookie_count,
        "user_data_dir": str(u),
        "user_data_exists": u.exists(),
        "cookie_candidates": present_candidates,
        "error": err,
    }
