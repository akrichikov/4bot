from pathlib import Path
from xbot.profiles import storage_state_path, user_data_dir, cookie_candidates, validate


def test_storage_state_path_prefers_config(tmp_path, monkeypatch):
    # Create a fake config/profiles/foo/storageState.json
    p = Path('config/profiles/foo')
    p.mkdir(parents=True, exist_ok=True)
    f = p / 'storageState.json'
    f.write_text('{"cookies": []}', encoding='utf-8')
    # auth legacy also present should be ignored when prefer_config_dir=True
    a = Path('auth/foo')
    a.mkdir(parents=True, exist_ok=True)
    (a / 'storageState.json').write_text('{"cookies": []}', encoding='utf-8')

    resolved = storage_state_path('foo')
    assert str(resolved) == str(f)


def test_user_data_dir_default_and_named():
    assert str(user_data_dir('default')) == '.x-user'
    assert str(user_data_dir('work')) == '.x-user/work'


def test_cookie_candidates_list_paths():
    cands = cookie_candidates('foo')
    # basic shape and expected last two entries
    assert any('auth_data/x_cookies.json' in str(p) for p in cands)
    assert str(cands[-1]).endswith('auth/foo/storageState.json')


def test_validate_profile():
    # Create a minimal storage for bar
    sp = Path('auth/bar')
    sp.mkdir(parents=True, exist_ok=True)
    (sp / 'storageState.json').write_text('{"cookies": [{"name":"auth_token","value":"x","domain":".x.com"}]}', encoding='utf-8')
    info = validate('bar')
    assert info['profile'] == 'bar'
    assert info['storage_exists'] is True
    assert info['cookie_count'] >= 1
