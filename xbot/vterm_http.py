from __future__ import annotations

# Backward-compatible re-export of HTTP server from the standalone ptyterm package.
try:
    from ptyterm.vterm_http import VTermHTTPServer  # type: ignore[F401]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "ptyterm package not found. Run: 'make submodules-init && make deps-pty' or 'pip install -e submodules/ptyterm'"
    ) from e

__all__ = ["VTermHTTPServer"]
