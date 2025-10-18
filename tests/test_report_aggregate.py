from xbot.report_aggregate import aggregate_status


def test_aggregate_status_combines_sources():
    health = {"cookies": {"count": 2, "keys_present": ["auth_token"]},
              "storage": {"exists": True, "cookie_count": 2},
              "vterm_http": {"ok": True, "status": 200},
              "rabbitmq": {"ok": True}}
    guard = {"summary": {"PASS": 5, "EDIT": 1, "BLOCK": 0}}
    sched = {"counts": {"a": 10, "b": 20}}
    rep = aggregate_status(health, guard, sched)
    assert rep["health"]["present"] is True and rep["health"]["ok"] is True
    assert rep["guardrails"]["summary"]["PASS"] == 5
    assert rep["scheduler"]["counts"]["b"] == 20
