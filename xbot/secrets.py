from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict


@dataclass
class _Backend:
    kind: str
    path: Optional[Path] = None
    cache: Optional[Dict[str, str]] = None


def _backend() -> _Backend:
    file_path = os.getenv("XBOT_SECRETS_FILE")
    if file_path:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        else:
            data = {}
        return _Backend(kind="file", path=p, cache=data)
    # Process-local fallback (non-persistent)
    global _MEM
    try:
        _MEM
    except NameError:
        _MEM = {}
    return _Backend(kind="memory", cache=_MEM)


def get(name: str) -> Optional[str]:
    b = _backend()
    return (b.cache or {}).get(name)


def set(name: str, value: str) -> None:
    b = _backend()
    b.cache[name] = value
    if b.kind == "file" and b.path:
        b.path.write_text(json.dumps(b.cache, ensure_ascii=False, indent=2), encoding="utf-8")


def delete(name: str) -> bool:
    b = _backend()
    if name in b.cache:
        del b.cache[name]
        if b.kind == "file" and b.path:
            b.path.write_text(json.dumps(b.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    return False

