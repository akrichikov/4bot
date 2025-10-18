from __future__ import annotations

from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDE = {".git", ".venv", "node_modules", "artifacts", "logs", "x_in_memory_bot.egg-info", "__pycache__"}


def _iter_tree(root: Path, max_depth: int = 2, exclude: set[str] | None = None) -> list[tuple[int, Path]]:
    ex = set(exclude or set()) | DEFAULT_EXCLUDE
    out: list[tuple[int, Path]] = []
    root = root.resolve()

    def walk(p: Path, depth: int) -> None:
        if depth > max_depth:
            return
        if p.name in ex:
            return
        out.append((depth, p))
        if p.is_dir():
            for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if child.name in ex:
                    continue
                walk(child, depth + 1)

    walk(root, 0)
    return out


def write_repo_layout_md(out_path: Path, root: Path | None = None, max_depth: int = 2) -> Path:
    root = (root or Path(".")).resolve()
    lines: list[str] = []
    lines.append(f"# Repository Layout (depth={max_depth})\n")
    lines.append(f"Root: `{root}`\n")

    entries = _iter_tree(root, max_depth=max_depth)
    # Skip the first tuple (depth=0, root) for prettiness
    for depth, p in entries[1:]:
        rel = p.relative_to(root)
        indent = "  " * (depth - 1)
        bullet = "-"
        suffix = "/" if p.is_dir() else ""
        lines.append(f"{indent}{bullet} `{rel}{suffix}`")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path

