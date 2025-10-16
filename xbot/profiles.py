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
