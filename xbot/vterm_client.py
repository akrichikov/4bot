from __future__ import annotations

# Re-export client wrapper from ptyterm for backward compatibility.
try:
    from ptyterm.vterm_client import VTermClient  # type: ignore[F401]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "ptyterm package not found. Run: 'make submodules-init && make deps-pty' or 'pip install -e submodules/ptyterm'"
    ) from e

__all__ = ["VTermClient"]
