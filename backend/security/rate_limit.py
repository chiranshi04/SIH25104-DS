"""Simple process-local rate limiting for the public API."""

from collections import defaultdict, deque
from threading import Lock
import time

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please wait a minute and try again.",
                    headers={"Retry-After": str(window_seconds)},
                )
            events.append(now)


limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_ip_limit(request: Request, bucket: str, limit: int) -> None:
    limiter.check(f"{bucket}:ip:{client_ip(request)}", limit)


def enforce_user_limit(request: Request, bucket: str, user_id: int, limit: int) -> None:
    limiter.check(f"{bucket}:user:{user_id}", limit)
