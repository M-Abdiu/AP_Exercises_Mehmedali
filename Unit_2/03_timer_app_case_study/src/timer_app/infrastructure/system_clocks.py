"""Concrete clock adapters.

These classes implement the clock protocols using the system clock sources.

- Wall clock uses :func:`datetime.datetime.now` in UTC.
- Monotonic clock uses :func:`time.monotonic`.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from timer_app.ports.clocks import MonotonicClock, WallClock


class SystemWallClock(WallClock):
    """System wall-clock implementation."""

    def now_utc(self) -> datetime:
        """Return current UTC time as a timezone-aware datetime."""
        return datetime.now(tz=UTC)


class SystemMonotonicClock(MonotonicClock):
    """System monotonic clock implementation."""

    def now(self) -> float:
        """Return monotonic timestamp in fractional seconds."""
        return time.monotonic()
