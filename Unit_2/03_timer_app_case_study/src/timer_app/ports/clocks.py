"""Clock port interfaces.

The application layer depends on these protocols so it can be tested with
deterministic clocks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class WallClock(Protocol):
    """Wall-clock time provider (subject to system clock changes)."""

    def now_utc(self) -> datetime:
        """Return current UTC datetime (timezone-aware)."""


class MonotonicClock(Protocol):
    """Monotonic time provider (not subject to system clock changes)."""

    def now(self) -> float:
        """Return monotonic timestamp in seconds."""
