from xbot.safety import evaluate_list


def test_evaluate_list_counts():
    lines = [
        "Keep building.",  # PASS
        "Email me at test@example.com",  # EDIT
        "visit https://bad.example.com",  # BLOCK
    ]
    rep = evaluate_list(lines)
    assert rep["summary"]["PASS"] == 1
    assert rep["summary"]["EDIT"] == 1
    assert rep["summary"]["BLOCK"] == 1
