from pathlib import Path
from xbot.report_health import write_system_health_html


def test_write_system_health_with_guardrails(tmp_path):
    report = {
        "cookies": {"count": 2, "keys_present": ["auth_token"]},
        "storage": {"path": "auth/storageState.json", "exists": True, "cookie_count": 2},
        "vterm_http": {"ok": True, "status": 200, "latency_ms": 10, "base": "http://127.0.0.1:8765"},
        "rabbitmq": {"ok": True},
    }
    guard = {"summary": {"PASS": 3, "EDIT": 1, "BLOCK": 0}}
    out = tmp_path / "health.html"
    path = write_system_health_html(report, out, guard=guard)
    html = path.read_text(encoding="utf-8")
    assert "Guardrails" in html
    assert "PASS: <strong>3</strong>" in html
    assert "EDIT: <strong>1</strong>" in html
