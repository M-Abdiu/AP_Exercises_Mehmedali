"""Repository port interfaces.

These protocols define how the application layer reads/writes domain entities
without tying itself to a concrete persistence implementation.
"""

from __future__ import annotations

from typing import Protocol

from timer_app.domain.models import Alarm, AppPreferences, Reminder


class AlarmRepository(Protocol):
    """CRUD access for :class:`timer_app.domain.models.Alarm` objects."""

    def list(self) -> list[Alarm]:
        """Return all stored alarms."""
        ...

    def get(self, alarm_id: str) -> Alarm:
        """Return the alarm with the given id."""
        ...

    def upsert(self, alarm: Alarm) -> None:
        """Insert or replace an alarm by id."""
        ...

    def delete(self, alarm_id: str) -> None:
        """Delete an alarm by id."""
        ...


class ReminderRepository(Protocol):
    """CRUD access for :class:`timer_app.domain.models.Reminder` objects."""

    def list(self) -> list[Reminder]:
        """Return all stored reminders."""
        ...

    def get(self, reminder_id: str) -> Reminder:
        """Return the reminder with the given id."""
        ...

    def upsert(self, reminder: Reminder) -> None:
        """Insert or replace a reminder by id."""
        ...

    def delete(self, reminder_id: str) -> None:
        """Delete a reminder by id."""
        ...


class WorldClockRepository(Protocol):
    """Storage access for the user-selected world clock time zone list."""

    def list_timezones(self) -> list[str]:
        """Return the stored list of IANA time zone identifiers."""
        ...

    def add_timezone(self, tz_id: str) -> None:
        """Add an IANA time zone identifier to the list."""
        ...

    def remove_timezone(self, tz_id: str) -> None:
        """Remove an IANA time zone identifier from the list."""
        ...


class PreferencesRepository(Protocol):
    """Storage access for persisted user preferences."""

    def get(self) -> AppPreferences:
        """Return current preferences."""
        ...

    def set(self, preferences: AppPreferences) -> None:
        """Persist new preferences."""
        ...
