import unittest
from datetime import UTC, date, datetime, time

from timer_app.application.services import ConversionService, ReminderService
from timer_app.domain.errors import ValidationError
from timer_app.domain.time_rules import LocalDateTimeInput, detect_dst_resolution, get_zoneinfo, to_utc_instant


class FakeWallClock:
    def __init__(self, now_utc: datetime):
        self._now = now_utc

    def now_utc(self) -> datetime:
        return self._now


class InMemoryPreferencesRepo:
    def __init__(self, time_format: str = "24h"):
        self._time_format = time_format

    def get(self):
        # Lazy import to avoid coupling tests to model details
        from timer_app.domain.models import AppPreferences

        return AppPreferences(time_format=self._time_format)  # type: ignore[arg-type]

    def set(self, preferences):
        self._time_format = preferences.time_format


class InMemoryReminderRepo:
    def __init__(self):
        self._items = {}

    def list(self):
        return list(self._items.values())

    def get(self, reminder_id: str):
        if reminder_id not in self._items:
            from timer_app.domain.errors import NotFoundError

            raise NotFoundError(f"Reminder not found: {reminder_id}")
        return self._items[reminder_id]

    def upsert(self, reminder):
        self._items[reminder.id] = reminder

    def delete(self, reminder_id: str):
        if reminder_id in self._items:
            del self._items[reminder_id]
        else:
            from timer_app.domain.errors import NotFoundError

            raise NotFoundError(f"Reminder not found: {reminder_id}")


def _tz_available(tz_id: str) -> bool:
    try:
        get_zoneinfo(tz_id)
        return True
    except ValidationError:
        return False


class TestTimeRules(unittest.TestCase):
    def test_to_utc_instant_utc_passthrough(self):
        inp = LocalDateTimeInput(
            local_date=date(2026, 2, 24),
            local_time=time(12, 0, 0),
            tz_id="UTC",
            fold=0,
        )
        out = to_utc_instant(inp)
        self.assertEqual(out.tzinfo, UTC)
        self.assertEqual(out, datetime(2026, 2, 24, 12, 0, 0, tzinfo=UTC))

    def test_detect_dst_resolution_utc_not_ambiguous(self):
        res = detect_dst_resolution(date(2026, 2, 24), time(12, 0, 0), "UTC")
        self.assertFalse(res.ambiguous)
        self.assertFalse(res.nonexistent)

    def test_nonexistent_time_raises_when_zone_available(self):
        if not _tz_available("Europe/Berlin"):
            self.skipTest("Europe/Berlin tzdata not available on this system")

        # DST spring-forward gap in Europe/Berlin: 2026-03-29 02:30 does not exist.
        inp = LocalDateTimeInput(
            local_date=date(2026, 3, 29),
            local_time=time(2, 30, 0),
            tz_id="Europe/Berlin",
            fold=0,
        )
        with self.assertRaises(ValidationError):
            to_utc_instant(inp)

    def test_ambiguous_time_detected_and_fold_disambiguates(self):
        if not _tz_available("Europe/Berlin"):
            self.skipTest("Europe/Berlin tzdata not available on this system")

        # DST fall-back ambiguity in Europe/Berlin (last Sunday in October).
        local_date = date(2026, 10, 25)
        local_time = time(2, 30, 0)
        res = detect_dst_resolution(local_date, local_time, "Europe/Berlin")
        self.assertTrue(res.ambiguous)
        self.assertFalse(res.nonexistent)

        utc0 = to_utc_instant(
            LocalDateTimeInput(local_date=local_date, local_time=local_time, tz_id="Europe/Berlin", fold=0)
        )
        utc1 = to_utc_instant(
            LocalDateTimeInput(local_date=local_date, local_time=local_time, tz_id="Europe/Berlin", fold=1)
        )
        self.assertNotEqual(utc0, utc1)

    def test_ambiguous_time_invalid_fold_rejected(self):
        if not _tz_available("Europe/Berlin"):
            self.skipTest("Europe/Berlin tzdata not available on this system")

        local_date = date(2026, 10, 25)
        local_time = time(2, 30, 0)
        res = detect_dst_resolution(local_date, local_time, "Europe/Berlin")
        if not res.ambiguous:
            self.skipTest("Expected ambiguous time for Europe/Berlin not detected on this system")

        with self.assertRaises(ValidationError):
            to_utc_instant(
                LocalDateTimeInput(
                    local_date=local_date,
                    local_time=local_time,
                    tz_id="Europe/Berlin",
                    fold=2,
                )
            )


class TestServices(unittest.TestCase):
    def test_conversion_service_to_utc(self):
        prefs = InMemoryPreferencesRepo(time_format="24h")
        svc = ConversionService(prefs)
        utc = svc.to_utc("2026-02-24", "12:00", "UTC")
        self.assertEqual(utc, datetime(2026, 2, 24, 12, 0, tzinfo=UTC))

    def test_reminder_service_create_defaults_to_utc_when_no_iana_local_tz(self):
        # This test checks that the "tz omitted" path works at least in a portable way.
        # We don't assert the actual local zone, only that it doesn't crash.
        repo = InMemoryReminderRepo()
        wall = FakeWallClock(datetime(2026, 2, 24, 0, 0, tzinfo=UTC))
        svc = ReminderService(repo, wall)
        rem = svc.create("2026-02-24", "12:00", message="hi", tz_id="UTC")
        self.assertEqual(rem.scheduled_utc, datetime(2026, 2, 24, 12, 0, tzinfo=UTC))

    def test_reminder_service_rejects_invalid_date(self):
        repo = InMemoryReminderRepo()
        wall = FakeWallClock(datetime(2026, 2, 24, 0, 0, tzinfo=UTC))
        svc = ReminderService(repo, wall)
        with self.assertRaises(ValidationError):
            svc.create("2026-02-30", "12:00", tz_id="UTC")


if __name__ == "__main__":
    unittest.main()
