import pytest

from app import rate_limit
from app.errors import RateLimitExceededError
from app.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limit_is_per_client_and_resets_after_window():
    clock = FakeClock()
    limiter = RateLimiter(max_requests=2, window_s=600, clock=clock)
    limiter.check("1.1.1.1")
    limiter.check("1.1.1.1")

    with pytest.raises(RateLimitExceededError):
        limiter.check("1.1.1.1")
    limiter.check("2.2.2.2")  # other clients are unaffected

    clock.now += 601
    limiter.check("1.1.1.1")  # window has passed


def test_error_message_states_the_limit():
    limiter = RateLimiter(max_requests=1, window_s=600, clock=FakeClock())
    limiter.check("ip")
    with pytest.raises(RateLimitExceededError) as info:
        limiter.check("ip")
    assert "1 briefs per 10 minutes" in info.value.message


def test_stale_clients_are_purged_to_bound_memory(monkeypatch):
    monkeypatch.setattr(rate_limit, "_MAX_TRACKED_CLIENTS", 2)
    clock = FakeClock()
    limiter = RateLimiter(max_requests=5, window_s=600, clock=clock)
    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        limiter.check(ip)

    clock.now += 601  # all three are now outside the window
    limiter.check("4.4.4.4")

    assert set(limiter._hits) == {"4.4.4.4"}
