"""Application services (use cases).

These classes implement the app's primary operations (create/list/delete/enable)
for alarms and reminders, and the read-only features (world clock, conversions).

They:
- Validate and parse user-facing inputs.
- Delegate time calculations to the domain layer.
- Persist changes via repository ports.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time
from uuid import uuid4

from timer_app.domain.errors import NotFoundError, ValidationError
from timer_app.domain.models import Alarm, AppPreferences, Reminder
from timer_app.domain.recurrence import next_alarm_fire_utc
from timer_app.domain.time_rules import (
    LocalDateTimeInput,
    format_dt,
    get_zoneinfo,
    system_local_tz,
    system_local_tz_id,
    to_utc_instant,
)
from timer_app.ports.clocks import WallClock
from timer_app.ports.repositories import (
    AlarmRepository,
    PreferencesRepository,
    ReminderRepository,
    WorldClockRepository,
)


def _parse_time_of_day(value: str) -> time:
    """Parse an ISO-like time-of-day string.

    Args:
        value: A string in ``HH:MM`` or ``HH:MM:SS`` format.

    Returns:
        A :class:`datetime.time` instance.

    Raises:
        ValidationError: If the string cannot be parsed.
    """

    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Time must be HH:MM or HH:MM:SS") from exc


def _parse_date(value: str) -> date:
    """Parse an ISO date string.

    Args:
        value: A string in ``YYYY-MM-DD`` format.

    Returns:
        A :class:`datetime.date` instance.

    Raises:
        ValidationError: If the string cannot be parsed.
    """

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Date must be YYYY-MM-DD") from exc


class AlarmService:
    """Use cases for managing alarms."""

    def __init__(self, alarms: AlarmRepository, clock: WallClock):
        """Create the service.

        Args:
            alarms: Alarm repository.
            clock: Wall clock for computing next occurrences.
        """

        self._alarms = alarms
        self._clock = clock

    def create(self, time_of_day: str, recurrence: str, label: str = "") -> Alarm:
        """Create and persist a new alarm.

        Args:
            time_of_day: Wall-clock time string (``HH:MM`` or ``HH:MM:SS``).
            recurrence: One of ``once``, ``daily``, or ``weekdays``.
            label: Optional label.

        Returns:
            The created :class:`~timer_app.domain.models.Alarm`.

        Raises:
            ValidationError: If inputs are invalid.
        """

        tod = _parse_time_of_day(time_of_day)
        if recurrence not in ("once", "daily", "weekdays"):
            raise ValidationError("recurrence must be once|daily|weekdays")

        alarm = Alarm(
            id=str(uuid4()),
            label=label,
            enabled=True,
            time_of_day=tod,
            recurrence=recurrence,  # type: ignore[arg-type]
            status="scheduled",
        )
        self._alarms.upsert(alarm)
        return alarm

    def list(self) -> list[Alarm]:
        """Return all persisted alarms."""
        return self._alarms.list()

    def delete(self, alarm_id: str) -> None:
        """Delete an alarm by id."""
        self._alarms.delete(alarm_id)

    def enable(self, alarm_id: str) -> Alarm:
        """Enable an alarm by id."""
        alarm = self._alarms.get(alarm_id)
        updated = replace(alarm, enabled=True)
        self._alarms.upsert(updated)
        return updated

    def disable(self, alarm_id: str) -> Alarm:
        """Disable an alarm by id."""
        alarm = self._alarms.get(alarm_id)
        updated = replace(alarm, enabled=False)
        self._alarms.upsert(updated)
        return updated

    def next_fire_display(self, alarm: Alarm, preferences: AppPreferences) -> str:
        """Return a human-readable next-fire time for an alarm.

        Args:
            alarm: The alarm to evaluate.
            preferences: Display preferences.

        Returns:
            A formatted local datetime string, or ``"-"`` if there is no next fire.
        """

        now = self._clock.now_utc()
        nf = next_alarm_fire_utc(alarm, now)
        if nf is None:
            return "-"
        return format_dt(nf.at_utc.astimezone(system_local_tz()), preferences.time_format)


class ReminderService:
    """Use cases for managing reminders."""

    def __init__(self, reminders: ReminderRepository, clock: WallClock):
        """Create the service.

        Args:
            reminders: Reminder repository.
            clock: Wall clock used for missed-reminder detection.
        """

        self._reminders = reminders
        self._clock = clock

    def create(
        self,
        date_str: str,
        time_str: str,
        message: str = "",
        tz_id: str | None = None,
        fold: int = 0,
    ) -> Reminder:
        """Create and persist a new reminder.

        The input is interpreted as a *local* date/time in the provided time zone
        (or in the system's local time zone when ``tz_id`` is omitted), then
        normalized to a UTC instant for storage.

        Args:
            date_str: Date in ``YYYY-MM-DD`` format.
            time_str: Time in ``HH:MM`` or ``HH:MM:SS`` format.
            message: Optional reminder message.
            tz_id: Optional IANA time zone id.
            fold: PEP 495 fold (0 or 1) used when the local time is ambiguous.

        Returns:
            The created :class:`~timer_app.domain.models.Reminder`.

        Raises:
            ValidationError: If inputs are invalid or the local time is non-existent.
        """

        local_date = _parse_date(date_str)
        local_time = _parse_time_of_day(time_str)

        tz = tz_id
        if tz is None:
            tz = system_local_tz_id()

        get_zoneinfo(tz)
        scheduled_utc = to_utc_instant(
            LocalDateTimeInput(local_date=local_date, local_time=local_time, tz_id=tz, fold=fold)
        )

        reminder = Reminder(
            id=str(uuid4()),
            message=message,
            enabled=True,
            scheduled_utc=scheduled_utc,
            source_tz=tz,
            status="scheduled",
        )
        self._reminders.upsert(reminder)
        return reminder

    def list(self) -> list[Reminder]:
        """Return all persisted reminders."""
        return self._reminders.list()

    def delete(self, reminder_id: str) -> None:
        """Delete a reminder by id."""
        self._reminders.delete(reminder_id)

    def enable(self, reminder_id: str) -> Reminder:
        """Enable a reminder and reset it to scheduled status."""
        reminder = self._reminders.get(reminder_id)
        updated = replace(reminder, enabled=True, status="scheduled")
        self._reminders.upsert(updated)
        return updated

    def disable(self, reminder_id: str) -> Reminder:
        """Disable a reminder by id."""
        reminder = self._reminders.get(reminder_id)
        updated = replace(reminder, enabled=False)
        self._reminders.upsert(updated)
        return updated

    def mark_missed_past_reminders(self) -> int:
        """Mark scheduled reminders in the past as missed.

        This implements the v0.1 missed-reminder policy (Req 16): on startup,
        past reminders are not fired; they are marked missed and disabled.

        Returns:
            The number of reminders updated.
        """

        now = self._clock.now_utc()
        updated = 0
        for reminder in self._reminders.list():
            if reminder.enabled and reminder.status == "scheduled" and reminder.scheduled_utc < now:
                self._reminders.upsert(replace(reminder, status="missed", enabled=False))
                updated += 1
        return updated


class WorldClockService:
    """Use cases for the world clock feature."""

    def __init__(
        self,
        world_clock: WorldClockRepository,
        preferences: PreferencesRepository,
        clock: WallClock,
    ):
        """Create the service.

        Args:
            world_clock: Repository for stored time zone list.
            preferences: Repository for display preferences.
            clock: Wall clock for computing current time.
        """

        self._world_clock = world_clock
        self._preferences = preferences
        self._clock = clock

    def add(self, tz_id: str) -> None:
        """Add a time zone to the world clock list."""
        self._world_clock.add_timezone(tz_id)

    def remove(self, tz_id: str) -> None:
        """Remove a time zone from the world clock list."""
        self._world_clock.remove_timezone(tz_id)

    def list(self) -> list[str]:
        """Return the stored world clock time zone ids."""
        return self._world_clock.list_timezones()

    def now_display(self) -> list[tuple[str, str]]:
        """Return current time in each configured world clock time zone."""
        prefs = self._preferences.get()
        now_utc = self._clock.now_utc()
        out: list[tuple[str, str]] = []
        for tz_id in self._world_clock.list_timezones():
            tz = get_zoneinfo(tz_id)
            out.append((tz_id, format_dt(now_utc.astimezone(tz), prefs.time_format)))
        return out


class ConversionService:
    """Use cases for date/time conversions."""

    def __init__(self, preferences: PreferencesRepository):
        """Create the service.

        Args:
            preferences: Repository providing time display preferences.
        """

        self._preferences = preferences

    def convert_timezone(
        self,
        date_str: str,
        time_str: str,
        source_tz: str,
        target_tz: str,
        fold: int = 0,
    ) -> tuple[datetime, datetime]:
        """Convert a local date/time from a source zone to a target zone.

        Args:
            date_str: Date in ``YYYY-MM-DD`` format.
            time_str: Time in ``HH:MM`` or ``HH:MM:SS`` format.
            source_tz: IANA time zone for the input.
            target_tz: IANA time zone for the output.
            fold: PEP 495 fold (0 or 1) for ambiguous local times.

        Returns:
            A tuple of ``(utc_instant, target_datetime)``.
        """

        local_date = _parse_date(date_str)
        local_time = _parse_time_of_day(time_str)
        get_zoneinfo(source_tz)
        get_zoneinfo(target_tz)

        utc = to_utc_instant(
            LocalDateTimeInput(local_date=local_date, local_time=local_time, tz_id=source_tz, fold=fold)
        )
        target = utc.astimezone(get_zoneinfo(target_tz))
        return utc, target

    def to_utc(
        self,
        date_str: str,
        time_str: str,
        source_tz: str,
        fold: int = 0,
    ) -> datetime:
        """Convert a local date/time in a source zone into a UTC instant."""

        local_date = _parse_date(date_str)
        local_time = _parse_time_of_day(time_str)
        get_zoneinfo(source_tz)
        return to_utc_instant(
            LocalDateTimeInput(local_date=local_date, local_time=local_time, tz_id=source_tz, fold=fold)
        )

    def format(self, dt: datetime) -> str:
        """Format a timezone-aware datetime using stored preferences."""
        prefs = self._preferences.get()
        return format_dt(dt, prefs.time_format)
