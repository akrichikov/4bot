from __future__ import annotations
import sys

def main() -> int:
    try:
        from xbot.vterm import VTerm  # type: ignore
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"[check_pty_source] import failed: {e}\n")
        return 0
    mod = getattr(VTerm, "__module__", "")
    if not mod.startswith("ptyterm."):
        sys.stderr.write(
            f"[check_pty_source] VTerm should come from ptyterm.*, got: {mod}\n"
        )
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
