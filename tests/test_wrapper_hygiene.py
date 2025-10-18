import py_compile
from pathlib import Path


WRAPPERS = [
    Path('scripts/notification/notification_json_parser.py'),
    Path('scripts/notification/working_notification_json_parser.py'),
]


def test_wrappers_compile():
    for p in WRAPPERS:
        assert p.exists(), f"Missing wrapper: {p}"
        py_compile.compile(str(p), doraise=True)


def test_wrappers_are_thin_shims():
    # Guard against reintroducing canonical classes/schemas into wrappers
    forbidden_tokens = [
        'class ParsedNotification',
        'class NotificationMetrics',
        'class PostContent',
    ]
    required_import = 'from xbot.notification_json_parser import NotificationJSONParser'

    for p in WRAPPERS:
        text = p.read_text(encoding='utf-8')
        assert required_import in text, f"Wrapper missing canonical import: {p}"
        for token in forbidden_tokens:
            assert token not in text, f"Wrapper should not embed canonical schemas: {p} contains {token!r}"

