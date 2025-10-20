from __future__ import annotations

# Backward-compatible re-export of HTTP server from the standalone ptyterm package.
from ptyterm.vterm_http import VTermHTTPServer  # type: ignore[F401]

__all__ = ["VTermHTTPServer"]

