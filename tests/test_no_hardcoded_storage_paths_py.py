from pathlib import Path


def test_no_hardcoded_profile_storage_paths_in_python_sources():
    # Protect against reintroducing config/profiles/4botbsc/storageState.json literal in python files
    roots = [Path('apps'), Path('scripts'), Path('xbot')]
    literal = 'config/profiles/4botbsc/storageState.json'
    offenders = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('*.py'):
            if 'tests' in p.parts or 'Docs' in p.parts:
                continue
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if literal in txt:
                offenders.append(str(p))
    assert not offenders, f"Hardcoded storageState path found in: {offenders}"

