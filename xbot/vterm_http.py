from __future__ import annotations

from pathlib import Path
import sys

def _import_ptyterm_http():
    try:
        from ptyterm.vterm_http import VTermHTTPServer  # type: ignore
        return VTermHTTPServer
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
            from ptyterm.vterm_http import VTermHTTPServer  # type: ignore
            return VTermHTTPServer
        sub = str(root / "submodules" / "ptyterm")
        if sub not in sys.path:
            sys.path.insert(0, sub)
        from ptyterm.vterm_http import VTermHTTPServer  # type: ignore
        return VTermHTTPServer

VTermHTTPServer = _import_ptyterm_http()

__all__ = ["VTermHTTPServer"]
