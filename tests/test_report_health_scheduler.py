from pathlib import Path
from xbot.report_health import write_system_health_html


def test_write_system_health_with_scheduler(tmp_path):
    report = {
        "cookies": {"count": 1, "keys_present": ["auth_token"]},
        "storage": {"exists": True, "cookie_count": 1},
        "vterm_http": {"ok": True, "status": 200},
        "rabbitmq": {"ok": True},
    }
    sched = {"counts": {"alpha": 5, "beta": 10}}
    out = tmp_path / "health.html"
    path = write_system_health_html(report, out, guard=None, sched=sched)
    html = path.read_text(encoding="utf-8")
    assert "Scheduler" in html
    assert "alpha" in html and "5" in html
    assert "beta" in html and "10" in html

