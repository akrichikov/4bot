def test_health_imports():
    import xbot.health as h
    assert hasattr(h, 'run_selector_health')
