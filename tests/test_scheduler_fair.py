from datetime import datetime, timedelta
from xbot.scheduler_fair import Policy, ProfileScheduler


def _t0():
    return datetime(2025, 1, 1, 12, 0, 0)


def test_fair_ratio_two_profiles():
    # a:1 rps, burst 10; b:2 rps, burst 10
    pols = [Policy('a', 1.0, 10), Policy('b', 2.0, 10)]
    sch = ProfileScheduler(pols)
    now = _t0()
    end = now + timedelta(seconds=10)
    counts = {'a': 0, 'b': 0}
    cur = now
    while cur < end:
        name = sch.pick_next_ready(cur)
        if name:
            sch.record(name, cur)
            counts[name] += 1
        # advance time by small step to allow accrual; 0.1s step
        cur += timedelta(milliseconds=100)
    # In 10s, expect about ~10 for 'a' and ~20 for 'b' within tolerance
    assert counts['b'] > counts['a']
    ratio = counts['b'] / max(1, counts['a'])
    assert 1.5 <= ratio <= 2.5


def test_quiet_hours_suppresses_profile():
    pols = [
        Policy('quiet', 10.0, 10, quiet_start='12:00', quiet_end='13:00'),
        Policy('active', 10.0, 10),
    ]
    sch = ProfileScheduler(pols)
    now = datetime(2025, 1, 1, 12, 15, 0)
    # quiet profile should not be selected
    for _ in range(20):
        name = sch.pick_next_ready(now)
        if name:
            sch.record(name, now)
            assert name == 'active'

