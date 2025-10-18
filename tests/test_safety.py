from xbot.safety import analyze, guardrail


def test_guardrail_pass():
    d, out = guardrail("Keep building. 4.")
    assert d == "PASS" and out == "Keep building. 4."


def test_guardrail_edit_pii():
    d, out = guardrail("Contact me: test@example.com or +1 555-123-4567")
    assert d == "EDIT"
    assert "[redacted" in out


def test_guardrail_block_links_and_profanity():
    d, out = guardrail("Check this: https://bad.example.com you idiot")
    assert d == "BLOCK" and out == ""

