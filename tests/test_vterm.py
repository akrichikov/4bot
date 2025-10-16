from __future__ import annotations

import json

from xbot.vterm import VTerm


def test_vterm_echo_and_json_parsing():
    vt = VTerm()
    try:
        res = vt.run("echo hello")
        assert res.exit_code == 0
        assert any("hello" in ln for ln in res.lines)

        res2 = vt.run("printf '%s\n' '{\"a\":1,\"b\":2}'")
        assert res2.exit_code == 0
        assert res2.json_objects and res2.json_objects[0]["a"] == 1
    finally:
        vt.close()


def test_vterm_key_values_and_table():
    vt = VTerm()
    try:
        res = vt.run("printf 'a=1\\nb: 2\\n' ")
        assert res.exit_code == 0
        assert res.key_values.get("a") == "1"
        assert res.key_values.get("b") == "2"

        res2 = vt.run("printf $'NAME  AGE  CITY\\nalice  30   nyc\\nbob    28   sf\\n'")
        assert res2.exit_code == 0
        assert res2.table is not None
        assert res2.table["headers"] == ["NAME", "AGE", "CITY"]
        assert res2.table["rows"][0]["NAME"].lower() == "alice"
    finally:
        vt.close()
