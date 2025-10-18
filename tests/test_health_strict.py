from xbot.health import evaluate_health_gates


def test_evaluate_health_gates_ok():
    report = {
        "cookies": {"count": 2, "keys_present": ["auth_token", "ct0"]},
        "storage": {"exists": True, "cookie_count": 2},
        "vterm_http": {"ok": True},
        "rabbitmq": {"ok": True},
    }
    ok, reasons = evaluate_health_gates(report)
    assert ok and reasons == []


def test_evaluate_health_gates_failures():
    report = {
        "cookies": {"count": 0, "keys_present": []},
        "storage": {"exists": False, "cookie_count": 0},
        "vterm_http": {"ok": False},
        "rabbitmq": {"ok": False},
    }
    ok, reasons = evaluate_health_gates(report)
    assert not ok
    # All four categories present in reasons (order not guaranteed)
    for k in ("cookies", "storage", "vterm_http", "rabbitmq"):
        assert k in reasons

