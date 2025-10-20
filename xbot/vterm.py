from __future__ import annotations

# Re-export the single source of truth from the standalone ptyterm package.
# Robust fallback: if an installed ptyterm is missing modules, try the vendored
# submodule path at submodules/ptyterm before failing.
from pathlib import Path
import sys

def _import_ptyterm():
    try:
        from ptyterm import VTerm, VTermResult  # type: ignore
        return VTerm, VTermResult
    except Exception:
        import sys as _sys
        _sys.modules.pop("ptyterm", None)
        root = Path(__file__).resolve().parents[1]
        pkg_dir = root / "submodules" / "ptyterm" / "ptyterm"
        if pkg_dir.is_dir():
            import types as _types
            pkg = _types.ModuleType("ptyterm")
            pkg.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]
            pkg.__file__ = str(pkg_dir / "__init__.py")
            _sys.modules["ptyterm"] = pkg
            from ptyterm.vterm import VTerm, VTermResult  # type: ignore
            return VTerm, VTermResult
        # fallback to adding submodule root to sys.path
        sub = str(root / "submodules" / "ptyterm")
        if sub not in sys.path:
            sys.path.insert(0, sub)
        from ptyterm import VTerm, VTermResult  # type: ignore
        return VTerm, VTermResult

VTerm, VTermResult = _import_ptyterm()

__all__ = ["VTerm", "VTermResult"]
