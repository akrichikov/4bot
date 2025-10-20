from __future__ import annotations

from pathlib import Path
import sys

def _import_ptyterm_vtermd():
    try:
        from ptyterm.vtermd import VTermDaemon, client_request, DEFAULT_SOCKET  # type: ignore
        return VTermDaemon, client_request, DEFAULT_SOCKET
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
            from ptyterm.vtermd import VTermDaemon, client_request, DEFAULT_SOCKET  # type: ignore
            return VTermDaemon, client_request, DEFAULT_SOCKET
        sub = str(root / "submodules" / "ptyterm")
        if sub not in sys.path:
            sys.path.insert(0, sub)
        from ptyterm.vtermd import VTermDaemon, client_request, DEFAULT_SOCKET  # type: ignore
        return VTermDaemon, client_request, DEFAULT_SOCKET

VTermDaemon, client_request, DEFAULT_SOCKET = _import_ptyterm_vtermd()

__all__ = ["VTermDaemon", "client_request", "DEFAULT_SOCKET"]
