from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .config import Config


IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
GIF_MIMES = {"image/gif"}
VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
}


@dataclass
class MediaValidation:
    ok: bool
    reasons: List[str]
    files: List[Path]


def validate_files(cfg: Config, files: Iterable[Path]) -> MediaValidation:
    reasons: List[str] = []
    accepted: List[Path] = []
    for f in files:
        p = Path(f)
        if not p.exists():
            reasons.append(f"missing: {p}")
            continue
        if p.stat().st_size > cfg.media_max_bytes:
            reasons.append(f"too_large: {p}")
            continue
        mime, _ = mimetypes.guess_type(str(p))
        if mime is None:
            reasons.append(f"unknown_type: {p}")
            continue
        if (mime in IMAGE_MIMES and not cfg.media_allow_images) or (
            mime in GIF_MIMES and not cfg.media_allow_gif
        ) or (mime in VIDEO_MIMES and not cfg.media_allow_video):
            reasons.append(f"type_blocked:{mime}:{p}")
            continue
        if mime not in IMAGE_MIMES | GIF_MIMES | VIDEO_MIMES:
            reasons.append(f"unsupported:{mime}:{p}")
            continue
        accepted.append(p)
    return MediaValidation(ok=len(accepted) > 0 and len(reasons) == 0, reasons=reasons, files=accepted)


def order_files(files: Iterable[Path]) -> List[Path]:
    def key(p: Path) -> int:
        mime, _ = mimetypes.guess_type(str(p))
        if mime in GIF_MIMES:
            return 2
        if mime in VIDEO_MIMES:
            return 3
        return 1  # images first
    return sorted([Path(f) for f in files], key=key)


def files_metadata(files: Iterable[Path]) -> List[dict]:
    out: List[dict] = []
    for f in files:
        p = Path(f)
        mime, _ = mimetypes.guess_type(str(p))
        try:
            size = p.stat().st_size
        except Exception:
            size = None
        out.append({"path": str(p), "mime": mime, "bytes": size})
    return out


def cap_files(files: Iterable[Path]) -> tuple[List[Path], dict]:
    """Apply X constraints: up to 4 photos OR 1 video/GIF. If mixed, prefer first video/GIF.
    Returns (capped_files, cap_meta)."""
    files = [Path(f) for f in files]
    imgs: List[Path] = []
    vids: List[Path] = []
    gifs: List[Path] = []
    for p in files:
        mime, _ = mimetypes.guess_type(str(p))
        if mime in IMAGE_MIMES:
            imgs.append(p)
        elif mime in GIF_MIMES:
            gifs.append(p)
        elif mime in VIDEO_MIMES:
            vids.append(p)
        else:
            imgs.append(p)  # default to images bucket

    meta: dict = {"mode": None, "capped": False}
    if vids or gifs:
        # pick first of video or gif, prefer video order
        chosen = vids[:1] if vids else gifs[:1]
        meta["mode"] = "video" if vids else "gif"
        meta["capped"] = len(chosen) != len(files)
        return chosen, meta
    # images only
    chosen = imgs[:4]
    meta["mode"] = "images"
    meta["capped"] = len(chosen) != len(files)
    return chosen, meta
