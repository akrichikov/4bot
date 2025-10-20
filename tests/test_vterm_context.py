from __future__ import annotations

from xbot.vterm import VTerm


def test_vterm_context_manager_echo():
    with VTerm() as vt:
        res = vt.run("printf 'ok\n'")
        assert res.exit_code == 0
        assert any('ok' in ln for ln in res.lines)

