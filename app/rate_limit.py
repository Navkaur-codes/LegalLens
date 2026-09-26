"""In-memory, per-IP sliding-window rate limiter.

Per process only: counts reset on restart and are not shared between instances.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.errors import RateLimitExceededError

_MAX_TRACKED_CLIENTS = 10_000


class RateLimiter:
    def __init__(self, max_requests: int, window_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._max_requests = max_requests
        self._window_s = window_s
        self._clock = clock
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a request for `key`, or raise RateLimitExceededError if the window is full."""
        now = self._clock()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_CLIENTS:
                self._purge_stale(now)
            hits = self._hits[key]
            while hits and hits[0] <= now - self._window_s:
                hits.popleft()
            if len(hits) >= self._max_requests:
                minutes = max(1, round(self._window_s / 60))
                raise RateLimitExceededError(
                    f"You have reached the limit of {self._max_requests} briefs per {minutes} minutes. "
                    "Please try again later."
                )
            hits.append(now)

    def _purge_stale(self, now: float) -> None:
        """Forget clients with no requests inside the window, so memory stays bounded."""
        cutoff = now - self._window_s
        for key in [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency using the limiter stored on app.state."""
    client_ip = request.client.host if request.client else "unknown"
    request.app.state.rate_limiter.check(client_ip)
