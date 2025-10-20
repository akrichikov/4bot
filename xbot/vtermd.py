from __future__ import annotations

# Re-export VTerm UNIX-socket daemon and client helpers from ptyterm.
try:
    from ptyterm.vtermd import (  # type: ignore[F401]
        VTermDaemon,
        client_request,
        DEFAULT_SOCKET,
    )
except Exception as e:  # pragma: no cover
    raise ImportError(
        "ptyterm package not found. Run: 'make submodules-init && make deps-pty' or 'pip install -e submodules/ptyterm'"
    ) from e

__all__ = ["VTermDaemon", "client_request", "DEFAULT_SOCKET"]
