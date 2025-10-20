from __future__ import annotations

# Re-export client wrapper from ptyterm for backward compatibility.
from ptyterm.vterm_client import VTermClient  # type: ignore[F401]

__all__ = ["VTermClient"]
