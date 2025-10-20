from __future__ import annotations

# Single source of truth now lives in the standalone ptyterm package.
# This module re-exports the public API for backward compatibility.
from ptyterm import VTerm, VTermResult  # type: ignore[F401]

__all__ = ["VTerm", "VTermResult"]
