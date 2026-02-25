import unittest

from timer_app.application.timers import CountdownTimer, PomodoroConfig, PomodoroTimer


class FakeMonotonicClock:
    def __init__(self, t: float = 0.0):
        self._t = float(t)

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += float(seconds)


class TestCountdownTimer(unittest.TestCase):
    def test_remaining_ceil_behavior(self):
        clock = FakeMonotonicClock(0.0)
        timer = CountdownTimer(1)
        timer.start(clock)

        self.assertEqual(timer.remaining_seconds(clock), 1)

        clock.advance(0.1)
        self.assertEqual(timer.remaining_seconds(clock), 1)

        clock.advance(0.89)  # t=0.99
        self.assertEqual(timer.remaining_seconds(clock), 1)

        clock.advance(0.01)  # t=1.0
        self.assertEqual(timer.remaining_seconds(clock), 0)
        self.assertEqual(timer.state(), "completed")

    def test_pause_resume_affects_elapsed(self):
        clock = FakeMonotonicClock(0.0)
        timer = CountdownTimer(10)
        timer.start(clock)

        clock.advance(3.0)
        self.assertEqual(timer.remaining_seconds(clock), 7)

        timer.pause(clock)
        clock.advance(5.0)
        # While paused, time should not elapse from the user's perspective
        self.assertEqual(timer.remaining_seconds(clock), 7)

        timer.resume(clock)
        clock.advance(1.0)
        self.assertEqual(timer.remaining_seconds(clock), 6)

    def test_cancel_freezes_remaining(self):
        clock = FakeMonotonicClock(0.0)
        timer = CountdownTimer(5)
        timer.start(clock)
        clock.advance(2.0)
        timer.cancel()
        # Spec: canceled returns original duration (CLI interprets cancel as exit)
        self.assertEqual(timer.remaining_seconds(clock), 5)
        self.assertEqual(timer.state(), "canceled")


class TestPomodoroTimer(unittest.TestCase):
    def test_work_to_short_break_transition(self):
        clock = FakeMonotonicClock(0.0)
        cfg = PomodoroConfig(
            work_seconds=1,
            short_break_seconds=1,
            long_break_seconds=1,
            sessions_before_long_break=2,
        )
        p = PomodoroTimer(cfg)
        p.start(clock)
        self.assertEqual(p.phase(), "work")

        clock.advance(1.0)
        msg = p.tick(clock)
        self.assertEqual(msg, "Work complete. Starting short break.")
        self.assertEqual(p.phase(), "short_break")

    def test_long_break_every_n_sessions(self):
        clock = FakeMonotonicClock(0.0)
        cfg = PomodoroConfig(
            work_seconds=1,
            short_break_seconds=1,
            long_break_seconds=1,
            sessions_before_long_break=2,
        )
        p = PomodoroTimer(cfg)
        p.start(clock)

        # Finish work #1 -> short break
        clock.advance(1.0)
        self.assertEqual(p.tick(clock), "Work complete. Starting short break.")

        # Finish short break -> work
        clock.advance(1.0)
        self.assertEqual(p.tick(clock), "Break complete. Starting work.")

        # Finish work #2 -> long break
        clock.advance(1.0)
        self.assertEqual(p.tick(clock), "Work complete. Starting long break.")
        self.assertEqual(p.phase(), "long_break")

    def test_sessions_before_long_break_zero_is_hardened(self):
        clock = FakeMonotonicClock(0.0)
        cfg = PomodoroConfig(
            work_seconds=1,
            short_break_seconds=1,
            long_break_seconds=1,
            sessions_before_long_break=0,
        )
        p = PomodoroTimer(cfg)
        p.start(clock)

        clock.advance(1.0)
        msg = p.tick(clock)
        # With hardening, 0 is treated as 1, so every session triggers long break.
        self.assertEqual(msg, "Work complete. Starting long break.")
        self.assertEqual(p.phase(), "long_break")


if __name__ == "__main__":
    unittest.main()
