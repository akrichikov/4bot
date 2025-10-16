import os
import pytest


@pytest.mark.live
def test_env_vars_present_for_live():
    if not (os.getenv("X_USER") and os.getenv("X_PASSWORD")):
        pytest.skip("Live creds not set; skipping live test")
    assert True
