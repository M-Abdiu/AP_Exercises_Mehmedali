"""Alarm/reminder scheduler runtime.

The scheduler runs while the app is active and:
- Computes next fire instants for alarms.
- Fires reminders at their scheduled UTC instants.
- Emits notifications.
- Updates persisted entity status (fired/missed).

This module intentionally does not depend on a specific UI; it uses the
NotificationSink port.
"""

from __future__ import annotations

import heapq
import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

from timer_app.domain.errors import NotFoundError
from timer_app.domain.recurrence import next_alarm_fire_utc
from timer_app.domain.time_rules import format_dt, system_local_tz
from timer_app.ports.clocks import WallClock
from timer_app.ports.notifications import NotificationSink
from timer_app.ports.repositories import AlarmRepository, PreferencesRepository, ReminderRepository


EventType = Literal["alarm", "reminder"]


class SchedulerRuntime:
    """Runs alarms and reminders while the app is active."""

    def __init__(
        self,
        alarms: AlarmRepository,
        reminders: ReminderRepository,
        preferences: PreferencesRepository,
        clock: WallClock,
        notifications: NotificationSink,
    ):
        """Create a scheduler runtime.

        Args:
            alarms: Repository providing alarms.
            reminders: Repository providing reminders.
            preferences: Repository for time-format preferences.
            clock: Wall clock for scheduling.
            notifications: Notification sink for fired events and status updates.
        """

        self._alarms = alarms
        self._reminders = reminders
        self._preferences = preferences
        self._clock = clock
        self._notifications = notifications
        self._seq = 0

    def _next_seq(self) -> int:
        """Return the next heap tie-breaker sequence number."""

        self._seq += 1
        return self._seq

    def _schedule_all(self, heap: list[tuple[float, int, EventType, str]]) -> None:
        """Populate the heap with all currently schedulable events."""

        now = self._clock.now_utc()

        for alarm in self._alarms.list():
            nf = next_alarm_fire_utc(alarm, now)
            if nf is None:
                continue
            heapq.heappush(heap, (nf.at_utc.timestamp(), self._next_seq(), "alarm", alarm.id))

        for reminder in self._reminders.list():
            if reminder.enabled and reminder.status == "scheduled":
                heapq.heappush(
                    heap,
                    (reminder.scheduled_utc.timestamp(), self._next_seq(), "reminder", reminder.id),
                )

    def _mark_missed_reminders(self) -> int:
        """Mark scheduled reminders in the past as missed (Req 16)."""
        now = self._clock.now_utc()
        updated = 0
        for reminder in self._reminders.list():
            if reminder.enabled and reminder.status == "scheduled" and reminder.scheduled_utc < now:
                self._reminders.upsert(replace(reminder, status="missed", enabled=False))
                updated += 1
        return updated

    def run_forever(self) -> None:
        """Run the scheduler loop until interrupted.

        The loop sleeps in short intervals to keep Ctrl+C responsive and to
        handle multiple events firing at (roughly) the same time.
        """

        missed = self._mark_missed_reminders()
        if missed:
            self._notifications.notify("Scheduler", f"Marked {missed} reminder(s) as missed")

        heap: list[tuple[float, int, EventType, str]] = []
        self._schedule_all(heap)

        self._notifications.notify("Scheduler", "Running (Ctrl+C to stop)")

        try:
            while True:
                now_utc = self._clock.now_utc()

                if not heap:
                    time.sleep(0.5)
                    self._schedule_all(heap)
                    continue

                next_ts, _, event_type, entity_id = heap[0]
                delay = max(0.0, next_ts - now_utc.timestamp())

                # Sleep in small chunks so Ctrl+C is responsive.
                time.sleep(min(delay, 0.5))

                now_utc = self._clock.now_utc()
                due: list[tuple[float, int, EventType, str]] = []
                while heap and heap[0][0] <= now_utc.timestamp():
                    due.append(heapq.heappop(heap))

                if not due:
                    continue

                for _, _, et, eid in due:
                    if et == "alarm":
                        self._fire_alarm(eid, now_utc)
                    else:
                        self._fire_reminder(eid, now_utc)

                # Rebuild heap to reflect any state changes.
                heap.clear()
                self._schedule_all(heap)

        except KeyboardInterrupt:
            self._notifications.notify("Scheduler", "Stopped")

    def _fire_alarm(self, alarm_id: str, fired_at_utc: datetime) -> None:
        """Fire an alarm and persist its updated state."""
        try:
            alarm = self._alarms.get(alarm_id)
        except NotFoundError:
            self._notifications.notify("Scheduler", f"Alarm not found: {alarm_id}")
            return

        prefs = self._preferences.get()
        local_dt = fired_at_utc.astimezone(system_local_tz())
        when = format_dt(local_dt, prefs.time_format)
        label = alarm.label or alarm.id
        self._notifications.notify("Alarm", f"{label} (at {when})")

        if alarm.recurrence == "once":
            updated = replace(
                alarm,
                enabled=False,
                status="fired",
                last_fired_utc=fired_at_utc.astimezone(UTC),
            )
        else:
            updated = replace(alarm, last_fired_utc=fired_at_utc.astimezone(UTC), status="scheduled")

        self._alarms.upsert(updated)

    def _fire_reminder(self, reminder_id: str, fired_at_utc: datetime) -> None:
        """Fire a reminder and persist its updated state."""
        try:
            reminder = self._reminders.get(reminder_id)
        except NotFoundError:
            self._notifications.notify("Scheduler", f"Reminder not found: {reminder_id}")
            return

        if not reminder.enabled or reminder.status != "scheduled":
            return

        prefs = self._preferences.get()
        local_dt = fired_at_utc.astimezone(system_local_tz())
        when = format_dt(local_dt, prefs.time_format)
        msg = reminder.message or reminder.id
        self._notifications.notify("Reminder", f"{msg} (at {when})")

        updated = replace(
            reminder,
            enabled=False,
            status="fired",
            fired_utc=fired_at_utc.astimezone(UTC),
        )
        self._reminders.upsert(updated)
