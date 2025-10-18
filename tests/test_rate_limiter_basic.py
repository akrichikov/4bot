import asyncio
import time
from xbot.ratelimit import RateLimiter


def test_rate_limiter_disabled_immediate():
    rl = RateLimiter(2.0, 3.0, enabled=False)
    t0 = time.time()
    asyncio.run(rl.wait("x"))
    assert (time.time() - t0) < 0.05


def test_rate_limiter_first_call_no_wait():
    rl = RateLimiter(2.0, 3.0, enabled=True)
    t0 = time.time()
    asyncio.run(rl.wait("x"))
    assert (time.time() - t0) < 0.05


def test_rate_limiter_zero_window_immediate():
    rl = RateLimiter(0.0, 0.0, enabled=True)
    asyncio.run(rl.wait("a"))  # set last_ts
    t0 = time.time()
    asyncio.run(rl.wait("a"))
    assert (time.time() - t0) < 0.05

