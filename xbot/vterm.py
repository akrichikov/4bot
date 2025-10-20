from __future__ import annotations

# Single source of truth now lives in the standalone ptyterm package.
# This module re-exports the public API for backward compatibility.
try:
    from ptyterm import VTerm, VTermResult  # type: ignore[F401]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "ptyterm package not found. Run: 'make submodules-init && make deps-pty' or 'pip install -e submodules/ptyterm'"
    ) from e

__all__ = ["VTerm", "VTermResult"]
