import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, time
from pathlib import Path

from timer_app.application.scheduler import SchedulerRuntime
from timer_app.domain.errors import NotFoundError, StorageError
from timer_app.domain.models import Alarm, AppPreferences, Reminder
from timer_app.infrastructure.json_store import (
    JsonAlarmRepository,
    JsonPreferencesRepository,
    JsonReminderRepository,
    JsonStateStore,
    JsonWorldClockRepository,
)


class FakeWallClock:
    def __init__(self, now_utc: datetime):
        self._now = now_utc

    def now_utc(self) -> datetime:
        return self._now


class CapturingNotificationSink:
    def __init__(self):
        self.events = []

    def notify(self, title: str, message: str) -> None:
        self.events.append((title, message))


class TestJsonStateStore(unittest.TestCase):
    def test_creates_default_state_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = JsonStateStore(path)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(data["alarms"], [])

    def test_update_rolls_back_in_memory_on_flush_failure(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = JsonStateStore(path)
            original = store.state

            def bad_flush() -> None:
                raise StorageError("boom")

            store.flush = bad_flush  # type: ignore[assignment]

            with self.assertRaises(StorageError):
                store.update(lambda st: replace(st, alarms=[]))

            # In-memory state should be restored
            self.assertIs(store.state, original)

    def test_load_rejects_unsupported_schema_version(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 999,
                        "alarms": [],
                        "reminders": [],
                        "world_clock_tzs": [],
                        "preferences": {"time_format": "24h"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(StorageError):
                JsonStateStore(path)

    def test_load_rejects_invalid_world_clock_timezone(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "alarms": [],
                        "reminders": [],
                        "world_clock_tzs": ["Not/AZone"],
                        "preferences": {"time_format": "24h"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(StorageError):
                JsonStateStore(path)

    def test_load_coerces_invalid_time_format_to_24h(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "alarms": [],
                        "reminders": [],
                        "world_clock_tzs": [],
                        "preferences": {"time_format": "nope"},
                    }
                ),
                encoding="utf-8",
            )
            store = JsonStateStore(path)
            self.assertEqual(store.state.preferences.time_format, "24h")


class TestRepositoriesAndScheduler(unittest.TestCase):
    def test_alarm_and_reminder_roundtrip_and_scheduler_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = JsonStateStore(path)
            alarms = JsonAlarmRepository(store)
            reminders = JsonReminderRepository(store)
            world = JsonWorldClockRepository(store)
            prefs = JsonPreferencesRepository(store)

            # preferences default
            self.assertEqual(prefs.get(), AppPreferences())

            # world clock add validates tz
            world.add_timezone("UTC")
            self.assertIn("UTC", world.list_timezones())

            # create an alarm and a reminder in storage
            alarm = Alarm(
                id="a1",
                label="",
                enabled=True,
                time_of_day=time(7, 30, 0),
                recurrence="once",
                status="scheduled",
                last_fired_utc=None,
            )
            alarms.upsert(alarm)
            self.assertEqual(alarms.get("a1"), alarm)

            now = datetime(2026, 2, 24, 12, 0, tzinfo=UTC)
            past = datetime(2026, 2, 24, 11, 59, tzinfo=UTC)
            reminder = Reminder(
                id="r1",
                message="hi",
                enabled=True,
                scheduled_utc=past,
                source_tz="UTC",
                status="scheduled",
                fired_utc=None,
            )
            reminders.upsert(reminder)

            # scheduler marks missed reminders on startup policy
            clock = FakeWallClock(now)
            sink = CapturingNotificationSink()
            runtime = SchedulerRuntime(
                alarms=alarms,
                reminders=reminders,
                preferences=prefs,
                clock=clock,
                notifications=sink,
            )
            missed = runtime._mark_missed_reminders()  # intentional white-box
            self.assertEqual(missed, 1)
            updated_rem = reminders.get("r1")
            self.assertEqual(updated_rem.status, "missed")
            self.assertFalse(updated_rem.enabled)

            # firing an alarm updates it (once -> fired+disabled)
            runtime._fire_alarm("a1", now)
            updated_alarm = alarms.get("a1")
            self.assertEqual(updated_alarm.status, "fired")
            self.assertFalse(updated_alarm.enabled)
            self.assertIsNotNone(updated_alarm.last_fired_utc)

    def test_persisting_naive_datetime_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonStateStore(Path(td) / "state.json")
            reminders = JsonReminderRepository(store)
            naive = datetime(2026, 2, 24, 12, 0)  # tzinfo=None
            reminder = Reminder(
                id="r1",
                message="",
                enabled=True,
                scheduled_utc=naive,  # type: ignore[arg-type]
                source_tz="UTC",
                status="scheduled",
                fired_utc=None,
            )
            with self.assertRaises(StorageError):
                reminders.upsert(reminder)

    def test_fire_reminder_noop_when_disabled_or_not_scheduled(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonStateStore(Path(td) / "state.json")
            reminders = JsonReminderRepository(store)
            prefs = JsonPreferencesRepository(store)
            alarms = JsonAlarmRepository(store)
            sink = CapturingNotificationSink()
            now = datetime(2026, 2, 24, 12, 0, tzinfo=UTC)
            runtime = SchedulerRuntime(
                alarms=alarms,
                reminders=reminders,
                preferences=prefs,
                clock=FakeWallClock(now),
                notifications=sink,
            )

            r_disabled = Reminder(
                id="r1",
                message="hi",
                enabled=False,
                scheduled_utc=now,
                source_tz="UTC",
                status="scheduled",
                fired_utc=None,
            )
            reminders.upsert(r_disabled)
            runtime._fire_reminder("r1", now)
            self.assertEqual(reminders.get("r1"), r_disabled)

            r_fired = replace(r_disabled, enabled=True, status="fired")
            reminders.upsert(r_fired)
            runtime._fire_reminder("r1", now)
            self.assertEqual(reminders.get("r1"), r_fired)

    def test_repository_get_missing_raises_notfound(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonStateStore(Path(td) / "state.json")
            alarms = JsonAlarmRepository(store)
            with self.assertRaises(NotFoundError):
                alarms.get("nope")

    def test_repository_delete_missing_raises_notfound(self):
        with tempfile.TemporaryDirectory() as td:
            store = JsonStateStore(Path(td) / "state.json")
            alarms = JsonAlarmRepository(store)
            reminders = JsonReminderRepository(store)
            world = JsonWorldClockRepository(store)

            with self.assertRaises(NotFoundError):
                alarms.delete("nope")
            with self.assertRaises(NotFoundError):
                reminders.delete("nope")
            with self.assertRaises(NotFoundError):
                world.remove_timezone("UTC")


if __name__ == "__main__":
    unittest.main()
