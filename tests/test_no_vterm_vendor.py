from __future__ import annotations

from xbot.vterm import VTerm


def test_vterm_module_origin_is_external():
    # Ensure VTerm class originates from the ptyterm package, not vendored code
    assert VTerm.__module__.startswith("ptyterm."), VTerm.__module__

