"""Recurrence and scheduling helpers.

This module contains logic for calculating the *next* trigger instant for alarms
based on their recurrence rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from timer_app.domain.models import Alarm
from timer_app.domain.time_rules import system_local_tz


@dataclass(frozen=True)
class NextFire:
    """Result of a next-fire computation.

    Attributes:
        at_utc: The next trigger instant in UTC.
        reason: Human-oriented explanation (useful for debugging).
    """

    at_utc: datetime
    reason: str


def _next_local_candidate(now_local: datetime, alarm: Alarm) -> datetime:
    """Return a local datetime candidate (today at time_of_day or next valid day)."""

    candidate = now_local.replace(
        hour=alarm.time_of_day.hour,
        minute=alarm.time_of_day.minute,
        second=alarm.time_of_day.second,
        microsecond=alarm.time_of_day.microsecond,
    )
    if candidate <= now_local:
        candidate = candidate + timedelta(days=1)
    return candidate


def next_alarm_fire_utc(alarm: Alarm, now_utc: datetime) -> NextFire | None:
    """Compute the next UTC trigger instant for an enabled alarm.

    This computes the next local wall-clock occurrence (today at the alarm time
    or a future day), applies recurrence rules, and converts to UTC.

    Args:
        alarm: Alarm to evaluate.
        now_utc: Current time in UTC.

    Returns:
        A :class:`NextFire` if the alarm should be scheduled; otherwise ``None``.
        ``None`` is returned if the alarm is disabled, or if a one-time alarm has
        already fired.
    """

    if not alarm.enabled:
        return None

    if alarm.recurrence == "once" and alarm.status == "fired":
        return None

    local_tz = system_local_tz()
    now_local = now_utc.astimezone(local_tz)

    candidate_local = _next_local_candidate(now_local, alarm)

    if alarm.recurrence == "weekdays":
        while candidate_local.weekday() >= 5:  # 5=Sat, 6=Sun
            candidate_local = candidate_local + timedelta(days=1)

    # candidate_local already has tzinfo; convert to UTC.
    return NextFire(at_utc=candidate_local.astimezone(UTC), reason="next occurrence")
