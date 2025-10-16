import json
from pathlib import Path


def test_fixture_storage_state_shape():
    p = Path("tests/fixtures/storageState_example.json")
    data = json.loads(p.read_text())
    assert isinstance(data.get("cookies"), list)
    assert isinstance(data.get("origins"), list)

