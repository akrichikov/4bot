from pathlib import Path


def test_no_absolute_user_paths_in_python_sources():
    # Scan Python sources under apps/, scripts/, xbot/ (exclude tests and Docs)
    roots = [Path('apps'), Path('scripts'), Path('xbot')]
    violations = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('*.py'):
            # Skip obvious vendor or cache paths if any
            if 'tests' in p.parts or 'Docs' in p.parts:
                continue
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if '/Users/' in txt:
                violations.append(str(p))
    assert not violations, f"Absolute /Users/ paths found in: {violations}"

