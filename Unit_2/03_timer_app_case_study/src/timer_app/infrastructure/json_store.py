"""JSON persistence adapters.

Persistence is implemented as a single JSON file containing the entire
:class:`timer_app.domain.models.AppState`.

Design goals:
- Simple, human-readable format appropriate for a small local app.
- Atomic writes (write temp + rename) to reduce corruption risk.
- Schema versioning to make future migrations possible.

This module contains:
- A :class:`JsonStateStore` that loads/saves the full state.
- Repository adapters (Alarm/Reminder/WorldClock/Preferences) that update parts
    of the state via the store.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any, Callable

from timer_app.domain.errors import NotFoundError, StorageError, ValidationError
from timer_app.domain.models import Alarm, AppPreferences, AppState, Reminder
from timer_app.domain.time_rules import get_zoneinfo
from timer_app.ports.repositories import (
    AlarmRepository,
    PreferencesRepository,
    ReminderRepository,
    WorldClockRepository,
)


_SCHEMA_VERSION = 1


def _default_state() -> AppState:
    """Return an empty initial app state."""
    return AppState(
        schema_version=_SCHEMA_VERSION,
        alarms=[],
        reminders=[],
        world_clock_tzs=[],
        preferences=AppPreferences(),
    )


def _dt_to_iso(dt: datetime | None) -> str | None:
    """Serialize an aware datetime to an ISO 8601 string in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        raise StorageError("Refusing to persist naive datetime")
    return dt.astimezone(UTC).isoformat()


def _dt_from_iso(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string and normalize to UTC."""
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise StorageError("Naive datetime found in storage")
    return dt.astimezone(UTC)


def _time_to_str(t: time) -> str:
    """Serialize a time-of-day to an ISO string."""
    return t.isoformat()


def _time_from_str(value: str) -> time:
    """Parse a time-of-day from an ISO string."""
    return time.fromisoformat(value)


class JsonStateStore:
    """Load/save the full app state to a single JSON file."""

    def __init__(self, path: Path):
        """Create the store and eagerly load existing state.

        Args:
            path: Path to the JSON file.
        """

        self._path = path
        self._state = self._load_or_init()

    @property
    def path(self) -> Path:
        """Return the JSON file path."""
        return self._path

    @property
    def state(self) -> AppState:
        """Return the currently loaded in-memory state."""
        return self._state

    def update(self, updater: Callable[[AppState], AppState]) -> None:
        """Apply an update function and persist the result.

        Args:
            updater: Function that takes the current state and returns a new state.
        """

        previous = self._state
        updated = updater(previous)
        self._state = updated
        try:
            self.flush()
        except Exception:
            # Keep in-memory state consistent with what's on disk.
            self._state = previous
            raise

    def flush(self) -> None:
        """Persist the current in-memory state to disk."""
        data = self._encode_state(self._state)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self._path)
        except StorageError:
            # Don't mask domain-level storage errors (e.g. invalid data).
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            raise StorageError(f"Failed to write storage: {self._path}") from exc

    def _load_or_init(self) -> AppState:
        """Load state from disk or initialize a new file."""
        if not self._path.exists():
            state = _default_state()
            self._state = state
            self.flush()
            return state

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return self._decode_state(data)
        except StorageError:
            raise
        except ValidationError as exc:
            raise StorageError(str(exc)) from exc
        except Exception as exc:
            raise StorageError(f"Failed to load storage: {self._path}") from exc

    # ---- encoding/decoding ----
    def _encode_state(self, state: AppState) -> dict[str, Any]:
        """Encode the in-memory state into a JSON-serializable dict."""
        return {
            "schema_version": state.schema_version,
            "alarms": [self._encode_alarm(a) for a in state.alarms],
            "reminders": [self._encode_reminder(r) for r in state.reminders],
            "world_clock_tzs": list(state.world_clock_tzs),
            "preferences": asdict(state.preferences),
        }

    def _decode_state(self, data: dict[str, Any]) -> AppState:
        """Decode a JSON object into an :class:`~timer_app.domain.models.AppState`.

        Raises:
            StorageError: If the schema version is unsupported or data is malformed.
        """

        version = int(data.get("schema_version", 0))
        if version != _SCHEMA_VERSION:
            raise StorageError(f"Unsupported schema version: {version}")

        alarms = [self._decode_alarm(a) for a in data.get("alarms", [])]
        reminders = [self._decode_reminder(r) for r in data.get("reminders", [])]
        world_clock = list(data.get("world_clock_tzs", []))

        prefs_raw = data.get("preferences", {})
        time_format = prefs_raw.get("time_format", "24h")
        if time_format not in ("24h", "12h"):
            time_format = "24h"
        prefs = AppPreferences(time_format=time_format)

        for tz_id in world_clock:
            get_zoneinfo(tz_id)

        return AppState(
            schema_version=_SCHEMA_VERSION,
            alarms=alarms,
            reminders=reminders,
            world_clock_tzs=world_clock,
            preferences=prefs,
        )

    def _encode_alarm(self, alarm: Alarm) -> dict[str, Any]:
        """Encode an alarm to JSON-serializable dict."""
        return {
            "id": alarm.id,
            "label": alarm.label,
            "enabled": alarm.enabled,
            "time_of_day": _time_to_str(alarm.time_of_day),
            "recurrence": alarm.recurrence,
            "status": alarm.status,
            "last_fired_utc": _dt_to_iso(alarm.last_fired_utc),
        }

    def _decode_alarm(self, data: dict[str, Any]) -> Alarm:
        """Decode an alarm object from JSON."""
        recurrence = data.get("recurrence", "daily")
        if recurrence not in ("once", "daily", "weekdays"):
            raise StorageError(f"Invalid alarm recurrence: {recurrence}")
        status = data.get("status", "scheduled")
        if status not in ("scheduled", "fired"):
            status = "scheduled"
        return Alarm(
            id=str(data["id"]),
            label=str(data.get("label", "")),
            enabled=bool(data.get("enabled", True)),
            time_of_day=_time_from_str(str(data["time_of_day"])),
            recurrence=recurrence,
            status=status,
            last_fired_utc=_dt_from_iso(data.get("last_fired_utc")),
        )

    def _encode_reminder(self, reminder: Reminder) -> dict[str, Any]:
        """Encode a reminder to JSON-serializable dict."""
        return {
            "id": reminder.id,
            "message": reminder.message,
            "enabled": reminder.enabled,
            "scheduled_utc": _dt_to_iso(reminder.scheduled_utc),
            "source_tz": reminder.source_tz,
            "status": reminder.status,
            "fired_utc": _dt_to_iso(reminder.fired_utc),
        }

    def _decode_reminder(self, data: dict[str, Any]) -> Reminder:
        """Decode a reminder object from JSON."""
        status = data.get("status", "scheduled")
        if status not in ("scheduled", "fired", "missed"):
            status = "scheduled"
        tz_id = str(data.get("source_tz", "UTC"))
        get_zoneinfo(tz_id)
        scheduled = _dt_from_iso(data.get("scheduled_utc"))
        if scheduled is None:
            raise StorageError("Reminder missing scheduled_utc")
        return Reminder(
            id=str(data["id"]),
            message=str(data.get("message", "")),
            enabled=bool(data.get("enabled", True)),
            scheduled_utc=scheduled,
            source_tz=tz_id,
            status=status,
            fired_utc=_dt_from_iso(data.get("fired_utc")),
        )


class JsonAlarmRepository(AlarmRepository):
    """Alarm repository adapter backed by :class:`JsonStateStore`."""

    def __init__(self, store: JsonStateStore):
        """Create the repository.

        Args:
            store: Shared JSON state store.
        """

        self._store = store

    def list(self) -> list[Alarm]:
        """Return all alarms."""
        return list(self._store.state.alarms)

    def get(self, alarm_id: str) -> Alarm:
        """Return a single alarm by id."""
        for alarm in self._store.state.alarms:
            if alarm.id == alarm_id:
                return alarm
        raise NotFoundError(f"Alarm not found: {alarm_id}")

    def upsert(self, alarm: Alarm) -> None:
        """Insert or replace an alarm and persist state."""
        def updater(state: AppState) -> AppState:
            alarms = [a for a in state.alarms if a.id != alarm.id]
            alarms.append(alarm)
            alarms.sort(key=lambda a: (a.time_of_day, a.id))
            return AppState(
                schema_version=state.schema_version,
                alarms=alarms,
                reminders=state.reminders,
                world_clock_tzs=state.world_clock_tzs,
                preferences=state.preferences,
            )

        self._store.update(updater)

    def delete(self, alarm_id: str) -> None:
        """Delete an alarm and persist state."""
        def updater(state: AppState) -> AppState:
            before = len(state.alarms)
            alarms = [a for a in state.alarms if a.id != alarm_id]
            if len(alarms) == before:
                raise NotFoundError(f"Alarm not found: {alarm_id}")
            return AppState(
                schema_version=state.schema_version,
                alarms=alarms,
                reminders=state.reminders,
                world_clock_tzs=state.world_clock_tzs,
                preferences=state.preferences,
            )

        self._store.update(updater)


class JsonReminderRepository(ReminderRepository):
    """Reminder repository adapter backed by :class:`JsonStateStore`."""

    def __init__(self, store: JsonStateStore):
        """Create the repository.

        Args:
            store: Shared JSON state store.
        """

        self._store = store

    def list(self) -> list[Reminder]:
        """Return all reminders."""
        return list(self._store.state.reminders)

    def get(self, reminder_id: str) -> Reminder:
        """Return a single reminder by id."""
        for reminder in self._store.state.reminders:
            if reminder.id == reminder_id:
                return reminder
        raise NotFoundError(f"Reminder not found: {reminder_id}")

    def upsert(self, reminder: Reminder) -> None:
        """Insert or replace a reminder and persist state."""
        def updater(state: AppState) -> AppState:
            reminders = [r for r in state.reminders if r.id != reminder.id]
            reminders.append(reminder)
            reminders.sort(key=lambda r: (r.scheduled_utc, r.id))
            return AppState(
                schema_version=state.schema_version,
                alarms=state.alarms,
                reminders=reminders,
                world_clock_tzs=state.world_clock_tzs,
                preferences=state.preferences,
            )

        self._store.update(updater)

    def delete(self, reminder_id: str) -> None:
        """Delete a reminder and persist state."""
        def updater(state: AppState) -> AppState:
            before = len(state.reminders)
            reminders = [r for r in state.reminders if r.id != reminder_id]
            if len(reminders) == before:
                raise NotFoundError(f"Reminder not found: {reminder_id}")
            return AppState(
                schema_version=state.schema_version,
                alarms=state.alarms,
                reminders=reminders,
                world_clock_tzs=state.world_clock_tzs,
                preferences=state.preferences,
            )

        self._store.update(updater)


class JsonWorldClockRepository(WorldClockRepository):
    """World clock repository adapter backed by :class:`JsonStateStore`."""

    def __init__(self, store: JsonStateStore):
        """Create the repository.

        Args:
            store: Shared JSON state store.
        """

        self._store = store

    def list_timezones(self) -> list[str]:
        """Return configured IANA time zone ids."""
        return list(self._store.state.world_clock_tzs)

    def add_timezone(self, tz_id: str) -> None:
        """Add a time zone id to the world clock list."""
        get_zoneinfo(tz_id)

        def updater(state: AppState) -> AppState:
            tzs = set(state.world_clock_tzs)
            tzs.add(tz_id)
            return AppState(
                schema_version=state.schema_version,
                alarms=state.alarms,
                reminders=state.reminders,
                world_clock_tzs=sorted(tzs),
                preferences=state.preferences,
            )

        self._store.update(updater)

    def remove_timezone(self, tz_id: str) -> None:
        """Remove a time zone id from the world clock list."""
        def updater(state: AppState) -> AppState:
            tzs = [t for t in state.world_clock_tzs if t != tz_id]
            if len(tzs) == len(state.world_clock_tzs):
                raise NotFoundError(f"Time zone not found in world clock: {tz_id}")
            return AppState(
                schema_version=state.schema_version,
                alarms=state.alarms,
                reminders=state.reminders,
                world_clock_tzs=tzs,
                preferences=state.preferences,
            )

        self._store.update(updater)


class JsonPreferencesRepository(PreferencesRepository):
    """Preferences repository adapter backed by :class:`JsonStateStore`."""

    def __init__(self, store: JsonStateStore):
        """Create the repository.

        Args:
            store: Shared JSON state store.
        """

        self._store = store

    def get(self) -> AppPreferences:
        """Return stored preferences."""
        return self._store.state.preferences

    def set(self, preferences: AppPreferences) -> None:
        """Persist preferences."""
        if preferences.time_format not in ("24h", "12h"):
            raise ValidationError("time_format must be '24h' or '12h'")

        def updater(state: AppState) -> AppState:
            return AppState(
                schema_version=state.schema_version,
                alarms=state.alarms,
                reminders=state.reminders,
                world_clock_tzs=state.world_clock_tzs,
                preferences=preferences,
            )

        self._store.update(updater)
