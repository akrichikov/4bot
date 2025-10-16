from xbot.profiles import profile_paths


def test_profile_paths_default_and_named():
    s, u = profile_paths("default")
    assert str(s) == "auth/storageState.json"
    assert str(u) == ".x-user"
    s2, u2 = profile_paths("work")
    assert str(s2) == "auth/work/storageState.json"
    assert str(u2) == ".x-user/work"
