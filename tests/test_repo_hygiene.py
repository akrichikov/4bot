from pathlib import Path


def test_repo_root_has_no_banned_files():
    root = Path('.')
    # Only check the repo base, do not recurse into subdirectories
    banned_patterns = [
        '*.sh', '*.plist', '*.json', '*.log', '*.png',
    ]
    banned = []
    for pat in banned_patterns:
        banned.extend(root.glob(pat))
    assert not banned, f"Banned files at repo root: {sorted(str(p) for p in banned)}"


def test_repo_root_has_no_marker_files():
    root = Path('.')
    assert not (root / '=1.3').exists(), "Marker file '=1.3' should not exist at repo root"
    assert not (root / '3.9').exists(), "Marker file '3.9' should not exist at repo root"

