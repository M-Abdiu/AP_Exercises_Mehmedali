"""Domain models for alarms, reminders, and persisted state.

The dataclasses in this module are intentionally simple and serializable.
They represent the core entities used by application services, persistence,
and scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, Optional


AlarmRecurrence = Literal["once", "daily", "weekdays"]


@dataclass(frozen=True)
class Alarm:
    """An alarm scheduled by local time-of-day.

    Policy (Req 34): alarms are evaluated in the user's current local time zone
    at scheduling/trigger time.

    For one-time alarms, the app fires at the next occurrence and then marks
    the alarm as fired (and auto-disables it).
    """

    id: str
    label: str
    enabled: bool
    time_of_day: time
    recurrence: AlarmRecurrence
    status: Literal["scheduled", "fired"] = "scheduled"
    last_fired_utc: Optional[datetime] = None


@dataclass(frozen=True)
class Reminder:
    """A reminder at a specific instant.

    Reminders are stored as UTC instants to avoid ambiguity.
    """

    id: str
    message: str
    enabled: bool
    scheduled_utc: datetime  # timezone-aware UTC
    source_tz: str
    status: Literal["scheduled", "fired", "missed"] = "scheduled"
    fired_utc: Optional[datetime] = None


@dataclass(frozen=True)
class AppPreferences:
    """User preferences persisted with the app state.

    Attributes:
        time_format: Display format for times.
            - ``"24h"`` for 24-hour time.
            - ``"12h"`` for 12-hour time with AM/PM.
    """

    time_format: Literal["24h", "12h"] = "24h"


@dataclass(frozen=True)
class AppState:
    """Root persisted state object.

    This is the top-level structure stored in JSON.

    Attributes:
        schema_version: Storage schema version for forward/backward
            compatibility.
        alarms: Alarm definitions.
        reminders: Reminder definitions.
        world_clock_tzs: IANA time zone identifiers selected for the world clock.
        preferences: User preferences.
    """

    schema_version: int
    alarms: list[Alarm]
    reminders: list[Reminder]
    world_clock_tzs: list[str]
    preferences: AppPreferences
