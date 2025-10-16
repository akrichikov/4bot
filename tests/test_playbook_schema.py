from pathlib import Path
from xbot.playbook import Playbook


def test_playbook_schema_loads():
    p = Path("playbooks/sample.json")
    pb = Playbook.from_path(p)
    assert len(pb.steps) == 3
    assert pb.steps[0].action == "login"
