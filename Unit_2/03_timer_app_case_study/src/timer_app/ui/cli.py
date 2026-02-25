"""Command-line interface (CLI) for the timer app.

This module is the app's composition root for the command-line experience.
It wires infrastructure adapters (JSON storage, clocks, notifications) to the
application services and exposes operations via :mod:`argparse` subcommands.

Persistence:
        By default, all state is stored in ``./data/timer_app.json``. Use
        ``--store`` to point at a different JSON file.

Runtime behavior:
        - Most commands perform a single action and exit (CRUD, world clock,
            conversions).
        - ``run`` starts the alarm/reminder scheduler loop and must remain running
            to fire events.
        - ``countdown`` and ``pomodoro`` run interactive loops until completion or
            Ctrl+C.
"""

from __future__ import annotations

import argparse
import sys
import time as _time
from pathlib import Path

from timer_app.application.scheduler import SchedulerRuntime
from timer_app.application.services import (
    AlarmService,
    ConversionService,
    ReminderService,
    WorldClockService,
)
from timer_app.application.timers import CountdownTimer, PomodoroConfig, PomodoroTimer
from timer_app.domain.errors import NotFoundError, TimerAppError, ValidationError
from timer_app.domain.recurrence import next_alarm_fire_utc
from timer_app.domain.time_rules import format_dt, system_local_tz
from timer_app.infrastructure.console_notifications import ConsoleNotificationSink
from timer_app.infrastructure.json_store import (
    JsonAlarmRepository,
    JsonPreferencesRepository,
    JsonReminderRepository,
    JsonStateStore,
    JsonWorldClockRepository,
)
from timer_app.infrastructure.system_clocks import SystemMonotonicClock, SystemWallClock


def _default_store_path() -> Path:
    """Return the default path for the JSON state file."""
    return Path("data") / "timer_app.json"


def _services(store_path: Path):
    """Create and wire concrete adapters used by the CLI.

    Args:
        store_path: Path to the JSON file used for persistence.

    Returns:
        Tuple containing the state store, repositories, clocks, and notification
        sink used by the CLI.

    Notes:
        The application layer depends on ports (protocols). This function is
        where we select specific infrastructure implementations.
    """
    store = JsonStateStore(store_path)
    alarms_repo = JsonAlarmRepository(store)
    reminders_repo = JsonReminderRepository(store)
    world_repo = JsonWorldClockRepository(store)
    prefs_repo = JsonPreferencesRepository(store)

    wall = SystemWallClock()
    mono = SystemMonotonicClock()
    notif = ConsoleNotificationSink()

    return store, alarms_repo, reminders_repo, world_repo, prefs_repo, wall, mono, notif


def _print_error(msg: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {msg}", file=sys.stderr)


def _parse_duration_seconds(value: str) -> int:
    """Parse a duration string into total seconds.

    The CLI accepts durations in one of the following formats:
    - ``SS``
    - ``MM:SS``
    - ``HH:MM:SS``

    Args:
        value: Duration string.

    Returns:
        Total duration in seconds.

    Raises:
        ValidationError: If parsing fails or the format is not supported.
    """

    parts = value.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError as exc:
        raise ValidationError("Duration must be SS, MM:SS, or HH:MM:SS") from exc

    if any(n < 0 for n in nums):
        raise ValidationError("Duration must be non-negative")

    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        mm, ss = nums
        if not (0 <= ss < 60):
            raise ValidationError("Duration seconds must be in 0..59")
        return mm * 60 + ss
    if len(nums) == 3:
        hh, mm, ss = nums
        if not (0 <= mm < 60 and 0 <= ss < 60):
            raise ValidationError("Duration minutes/seconds must be in 0..59")
        return hh * 3600 + mm * 60 + ss
    raise ValidationError("Duration must be SS, MM:SS, or HH:MM:SS")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional list of arguments (excluding the program name). If not
            provided, :mod:`argparse` uses :data:`sys.argv`.

    Returns:
        Exit status code (0 for success).
    """
    parser = argparse.ArgumentParser(prog="timer_app")
    parser.add_argument(
        "--store",
        type=Path,
        default=_default_store_path(),
        help="Path to JSON storage file (default: data/timer_app.json)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # ---- alarms ----
    alarms_p = sub.add_parser("alarms")
    alarms_sub = alarms_p.add_subparsers(dest="alarms_cmd", required=True)

    a_add = alarms_sub.add_parser("add")
    a_add.add_argument("time", help="HH:MM or HH:MM:SS")
    a_add.add_argument("--recurrence", default="daily", choices=["once", "daily", "weekdays"])
    a_add.add_argument("--label", default="")

    a_list = alarms_sub.add_parser("list")

    a_del = alarms_sub.add_parser("delete")
    a_del.add_argument("id")

    a_en = alarms_sub.add_parser("enable")
    a_en.add_argument("id")

    a_dis = alarms_sub.add_parser("disable")
    a_dis.add_argument("id")

    # ---- reminders ----
    rem_p = sub.add_parser("reminders")
    rem_sub = rem_p.add_subparsers(dest="rem_cmd", required=True)

    r_add = rem_sub.add_parser("add")
    r_add.add_argument("date", help="YYYY-MM-DD")
    r_add.add_argument("time", help="HH:MM or HH:MM:SS")
    r_add.add_argument("--tz", default=None, help="IANA tz id, e.g. Europe/Berlin")
    r_add.add_argument("--fold", type=int, default=0, help="0=earlier, 1=later (for ambiguous times)")
    r_add.add_argument("--message", default="")

    r_list = rem_sub.add_parser("list")

    r_del = rem_sub.add_parser("delete")
    r_del.add_argument("id")

    r_en = rem_sub.add_parser("enable")
    r_en.add_argument("id")

    r_dis = rem_sub.add_parser("disable")
    r_dis.add_argument("id")

    # ---- world clock ----
    wc_p = sub.add_parser("world")
    wc_sub = wc_p.add_subparsers(dest="wc_cmd", required=True)

    wc_add = wc_sub.add_parser("add")
    wc_add.add_argument("tz")

    wc_rm = wc_sub.add_parser("remove")
    wc_rm.add_argument("tz")

    wc_list = wc_sub.add_parser("list")

    wc_now = wc_sub.add_parser("now")

    # ---- conversions ----
    conv_p = sub.add_parser("convert")
    conv_sub = conv_p.add_subparsers(dest="conv_cmd", required=True)

    c_tz = conv_sub.add_parser("tz")
    c_tz.add_argument("date", help="YYYY-MM-DD")
    c_tz.add_argument("time", help="HH:MM or HH:MM:SS")
    c_tz.add_argument("source_tz")
    c_tz.add_argument("target_tz")
    c_tz.add_argument("--fold", type=int, default=0)

    c_utc = conv_sub.add_parser("utc")
    c_utc.add_argument("date", help="YYYY-MM-DD")
    c_utc.add_argument("time", help="HH:MM or HH:MM:SS")
    c_utc.add_argument("source_tz")
    c_utc.add_argument("--fold", type=int, default=0)

    # ---- scheduler run ----
    run_p = sub.add_parser("run", help="Run alarm/reminder scheduler")

    # ---- countdown ----
    cd_p = sub.add_parser("countdown")
    cd_p.add_argument("duration", help="SS or MM:SS or HH:MM:SS")

    # ---- pomodoro ----
    pomo_p = sub.add_parser("pomodoro")
    pomo_p.add_argument("--work", default="25:00", help="MM:SS")
    pomo_p.add_argument("--short", default="05:00", help="MM:SS")
    pomo_p.add_argument("--long", default="15:00", help="MM:SS")
    pomo_p.add_argument("--sessions", type=int, default=4)

    args = parser.parse_args(argv)

    try:
        (
            _store,
            alarms_repo,
            reminders_repo,
            world_repo,
            prefs_repo,
            wall,
            mono,
            notif,
        ) = _services(args.store)

        alarm_svc = AlarmService(alarms_repo, wall)
        reminder_svc = ReminderService(reminders_repo, wall)
        world_svc = WorldClockService(world_repo, prefs_repo, wall)
        conv_svc = ConversionService(prefs_repo)

        if args.cmd == "alarms":
            if args.alarms_cmd == "add":
                alarm = alarm_svc.create(args.time, args.recurrence, args.label)
                print(f"Created alarm {alarm.id}")
                return 0

            if args.alarms_cmd == "list":
                prefs = prefs_repo.get()
                now = wall.now_utc()
                for alarm in alarm_svc.list():
                    nf = next_alarm_fire_utc(alarm, now)
                    next_s = "-"
                    if nf is not None:
                        next_s = format_dt(nf.at_utc.astimezone(system_local_tz()), prefs.time_format)
                    print(
                        f"{alarm.id} enabled={alarm.enabled} recurrence={alarm.recurrence} time={alarm.time_of_day} next={next_s} label={alarm.label!r} status={alarm.status}"
                    )
                return 0

            if args.alarms_cmd == "delete":
                alarm_svc.delete(args.id)
                print("Deleted")
                return 0

            if args.alarms_cmd == "enable":
                alarm_svc.enable(args.id)
                print("Enabled")
                return 0

            if args.alarms_cmd == "disable":
                alarm_svc.disable(args.id)
                print("Disabled")
                return 0

        if args.cmd == "reminders":
            if args.rem_cmd == "add":
                rem = reminder_svc.create(
                    args.date,
                    args.time,
                    message=args.message,
                    tz_id=args.tz,
                    fold=args.fold,
                )
                print(f"Created reminder {rem.id} at {rem.scheduled_utc.isoformat()}")
                return 0

            if args.rem_cmd == "list":
                prefs = prefs_repo.get()
                local_tz = system_local_tz()
                for r in reminder_svc.list():
                    local = r.scheduled_utc.astimezone(local_tz)
                    print(
                        f"{r.id} enabled={r.enabled} status={r.status} when={format_dt(local, prefs.time_format)} source_tz={r.source_tz} message={r.message!r}"
                    )
                return 0

            if args.rem_cmd == "delete":
                reminder_svc.delete(args.id)
                print("Deleted")
                return 0

            if args.rem_cmd == "enable":
                reminder_svc.enable(args.id)
                print("Enabled")
                return 0

            if args.rem_cmd == "disable":
                reminder_svc.disable(args.id)
                print("Disabled")
                return 0

        if args.cmd == "world":
            if args.wc_cmd == "add":
                world_svc.add(args.tz)
                print("Added")
                return 0
            if args.wc_cmd == "remove":
                world_svc.remove(args.tz)
                print("Removed")
                return 0
            if args.wc_cmd == "list":
                for tz in world_svc.list():
                    print(tz)
                return 0
            if args.wc_cmd == "now":
                for tz_id, disp in world_svc.now_display():
                    print(f"{tz_id}: {disp}")
                return 0

        if args.cmd == "convert":
            if args.conv_cmd == "tz":
                utc, target = conv_svc.convert_timezone(
                    args.date, args.time, args.source_tz, args.target_tz, fold=args.fold
                )
                print(f"UTC:    {conv_svc.format(utc)}")
                print(f"Target: {conv_svc.format(target)}")
                return 0

            if args.conv_cmd == "utc":
                utc = conv_svc.to_utc(args.date, args.time, args.source_tz, fold=args.fold)
                print(conv_svc.format(utc))
                return 0

        if args.cmd == "run":
            runtime = SchedulerRuntime(
                alarms=alarms_repo,
                reminders=reminders_repo,
                preferences=prefs_repo,
                clock=wall,
                notifications=notif,
            )
            runtime.run_forever()
            return 0

        if args.cmd == "countdown":
            duration_s = _parse_duration_seconds(args.duration)
            if duration_s <= 0:
                raise ValidationError("Countdown duration must be > 0")
            timer = CountdownTimer(duration_s)
            timer.start(mono)
            print("Countdown started. Press Ctrl+C to cancel.")
            try:
                while True:
                    remaining = timer.remaining_seconds(mono)
                    print(f"Remaining: {remaining}s", end="\r", flush=True)
                    if remaining == 0:
                        print("\nDone")
                        notif.notify("Countdown", "Completed")
                        return 0
                    _time.sleep(0.2)
            except KeyboardInterrupt:
                print("\nCanceled")
                timer.cancel()
                return 0

        if args.cmd == "pomodoro":
            if args.sessions <= 0:
                raise ValidationError("--sessions must be > 0")
            cfg = PomodoroConfig(
                work_seconds=_parse_duration_seconds(args.work),
                short_break_seconds=_parse_duration_seconds(args.short),
                long_break_seconds=_parse_duration_seconds(args.long),
                sessions_before_long_break=args.sessions,
            )
            if cfg.work_seconds <= 0 or cfg.short_break_seconds <= 0 or cfg.long_break_seconds <= 0:
                raise ValidationError("Pomodoro durations must be > 0")
            pomo = PomodoroTimer(cfg)
            pomo.start(mono)
            notif.notify("Pomodoro", f"Started ({pomo.phase()})")
            try:
                while True:
                    msg = pomo.tick(mono)
                    remaining = pomo.remaining_seconds(mono)
                    print(f"{pomo.phase()} remaining: {remaining}s", end="\r", flush=True)
                    if msg:
                        print("\n" + msg)
                        notif.notify("Pomodoro", msg)
                    _time.sleep(0.2)
            except KeyboardInterrupt:
                print("\nStopped")
                pomo.stop()
                return 0

        _print_error("Unknown command")
        return 2

    except (ValidationError, NotFoundError) as exc:
        _print_error(str(exc))
        return 2
    except TimerAppError as exc:
        _print_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
