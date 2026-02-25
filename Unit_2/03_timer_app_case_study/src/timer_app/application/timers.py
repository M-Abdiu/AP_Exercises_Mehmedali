"""In-memory timers (countdown and pomodoro).

These timers are currently session-scoped (not persisted) and are designed to
use a monotonic clock (Req 20, Req 33) so they are resilient to system clock
changes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from timer_app.ports.clocks import MonotonicClock


@dataclass
class CountdownTimer:
    """In-memory countdown timer driven by a monotonic clock."""

    duration_seconds: int
    _state: str = "idle"  # idle|running|paused|completed|canceled
    _started_at: float | None = None
    _paused_at: float | None = None
    _paused_total: float = 0.0

    def start(self, clock: MonotonicClock) -> None:
        """Start the countdown.

        Calling start on an already-running/paused timer is a no-op.

        Args:
            clock: Monotonic clock provider.
        """

        if self._state not in ("idle", "completed", "canceled"):
            return
        self._state = "running"
        self._started_at = clock.now()
        self._paused_at = None
        self._paused_total = 0.0

    def pause(self, clock: MonotonicClock) -> None:
        """Pause the countdown if it is running."""
        if self._state != "running":
            return
        self._state = "paused"
        self._paused_at = clock.now()

    def resume(self, clock: MonotonicClock) -> None:
        """Resume the countdown if it is paused."""
        if self._state != "paused" or self._paused_at is None:
            return
        now = clock.now()
        self._paused_total += now - self._paused_at
        self._paused_at = None
        self._state = "running"

    def cancel(self) -> None:
        """Cancel the countdown."""
        self._state = "canceled"

    def state(self) -> str:
        """Return the current timer state."""
        return self._state

    def remaining_seconds(self, clock: MonotonicClock) -> int:
        """Compute the number of whole seconds remaining.

        The computation is based on elapsed monotonic time and total paused
        duration.

        Args:
            clock: Monotonic clock provider.

        Returns:
            Remaining seconds (never negative). When remaining time reaches
            zero, the timer transitions to the ``completed`` state.
        """

        if self._state in ("idle", "canceled"):
            return self.duration_seconds
        if self._started_at is None:
            return self.duration_seconds

        now = clock.now()
        paused_total = self._paused_total
        if self._state == "paused" and self._paused_at is not None:
            paused_total += now - self._paused_at

        elapsed = max(0.0, now - self._started_at - paused_total)
        duration = max(0, int(self.duration_seconds))
        remaining = int(math.ceil(duration - elapsed))
        if remaining <= 0 and self._state in ("running", "paused"):
            self._state = "completed"
            return 0
        return max(0, remaining)


@dataclass
class PomodoroConfig:
    """Pomodoro configuration values.

    All durations are expressed in seconds.
    """

    work_seconds: int = 25 * 60
    short_break_seconds: int = 5 * 60
    long_break_seconds: int = 15 * 60
    sessions_before_long_break: int = 4


@dataclass
class PomodoroTimer:
    """Pomodoro timer state machine.

    The pomodoro alternates between work and break phases based on
    :class:`PomodoroConfig`.
    """

    config: PomodoroConfig
    _phase: str = "idle"  # idle|work|short_break|long_break|stopped
    _session_count: int = 0
    _countdown: CountdownTimer | None = None

    def start(self, clock: MonotonicClock) -> None:
        """Start a new pomodoro cycle."""
        self._session_count = 0
        self._start_work(clock)

    def stop(self) -> None:
        """Stop the pomodoro and clear internal countdown state."""
        self._phase = "stopped"
        self._countdown = None

    def pause(self, clock: MonotonicClock) -> None:
        """Pause the current phase countdown, if any."""
        if self._countdown:
            self._countdown.pause(clock)

    def resume(self, clock: MonotonicClock) -> None:
        """Resume the current phase countdown, if any."""
        if self._countdown:
            self._countdown.resume(clock)

    def phase(self) -> str:
        """Return the current pomodoro phase name."""
        return self._phase

    def tick(self, clock: MonotonicClock) -> str | None:
        """Advance state; returns a message when a phase completes."""

        if self._countdown is None:
            return None

        remaining = self._countdown.remaining_seconds(clock)
        if remaining > 0:
            return None

        if self._phase == "work":
            self._session_count += 1
            sessions_before_long_break = max(1, int(self.config.sessions_before_long_break))
            if self._session_count % sessions_before_long_break == 0:
                self._start_long_break(clock)
                return "Work complete. Starting long break."
            self._start_short_break(clock)
            return "Work complete. Starting short break."

        if self._phase == "short_break":
            self._start_work(clock)
            return "Break complete. Starting work."

        if self._phase == "long_break":
            self._start_work(clock)
            return "Long break complete. Starting work."

        return None

    def remaining_seconds(self, clock: MonotonicClock) -> int:
        """Return remaining seconds in the current phase."""
        if not self._countdown:
            return 0
        return self._countdown.remaining_seconds(clock)

    def _start_work(self, clock: MonotonicClock) -> None:
        """Begin a work phase."""
        self._phase = "work"
        self._countdown = CountdownTimer(self.config.work_seconds)
        self._countdown.start(clock)

    def _start_short_break(self, clock: MonotonicClock) -> None:
        """Begin a short break phase."""
        self._phase = "short_break"
        self._countdown = CountdownTimer(self.config.short_break_seconds)
        self._countdown.start(clock)

    def _start_long_break(self, clock: MonotonicClock) -> None:
        """Begin a long break phase."""
        self._phase = "long_break"
        self._countdown = CountdownTimer(self.config.long_break_seconds)
        self._countdown.start(clock)
