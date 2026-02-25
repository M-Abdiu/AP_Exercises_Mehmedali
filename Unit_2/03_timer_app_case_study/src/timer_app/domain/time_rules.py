"""Time zone handling and conversions.

This module centralizes:
- IANA time zone loading (via :mod:`zoneinfo`).
- DST ambiguity / non-existence detection (Req 32) using a best-effort approach.
- Conversion from user-entered local date/time to an unambiguous UTC instant.

The app primarily stores scheduled instants (reminders) in UTC to avoid DST
edge-case surprises.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, tzinfo
from zoneinfo import ZoneInfo

from timer_app.domain.errors import ValidationError


@dataclass(frozen=True)
class LocalDateTimeInput:
    """User-supplied local date+time with time zone context."""

    local_date: date
    local_time: time
    tz_id: str
    fold: int = 0  # 0=earlier, 1=later (PEP 495)


def get_zoneinfo(tz_id: str) -> ZoneInfo:
    """Return :class:`zoneinfo.ZoneInfo` for an IANA time zone id.

    Args:
        tz_id: IANA time zone identifier (e.g. ``"Europe/Berlin"``).

    Returns:
        A ZoneInfo instance for the requested time zone.

    Raises:
        ValidationError: If the time zone id is not known on this system.
    """

    try:
        return ZoneInfo(tz_id)
    except Exception as exc:  # ZoneInfoNotFoundError is not always imported
        raise ValidationError(f"Unknown time zone: {tz_id}") from exc


def system_local_tz() -> tzinfo:
    """Best-effort local time zone.

    On some systems this is a :class:`zoneinfo.ZoneInfo` instance; otherwise it
    may be a fixed-offset :class:`datetime.tzinfo`, which is acceptable for
    scheduling within a session.
    """

    tz = datetime.now().astimezone().tzinfo
    if tz is None:
        # Extremely defensive: per CPython docs, astimezone() without args uses
        # the system local time zone, but keep a total fallback.
        return UTC
    return tz


def system_local_tz_id() -> str:
    """Return an IANA time zone id for the system local zone.

    If the system tzinfo is not a :class:`~zoneinfo.ZoneInfo` with an IANA key,
    this falls back to ``"UTC"``.
    """

    tz = system_local_tz()
    key = getattr(tz, "key", None)
    if isinstance(key, str) and key:
        return key
    return "UTC"


def _aware_local(dt_date: date, dt_time: time, tz: ZoneInfo, fold: int) -> datetime:
    """Build a timezone-aware local datetime for a wall date/time.

    Args:
        dt_date: Local calendar date.
        dt_time: Local wall-clock time.
        tz: Time zone for the local date/time.
        fold: PEP 495 fold value (0 or 1) used to disambiguate repeated times.

    Returns:
        A timezone-aware datetime in the given zone.
    """

    return datetime(
        dt_date.year,
        dt_date.month,
        dt_date.day,
        dt_time.hour,
        dt_time.minute,
        dt_time.second,
        dt_time.microsecond,
        tzinfo=tz,
        fold=fold,
    )


@dataclass(frozen=True)
class DstResolution:
    """DST status flags for a local date/time in a time zone."""

    ambiguous: bool
    nonexistent: bool


def detect_dst_resolution(local_date: date, local_time: time, tz_id: str) -> DstResolution:
    """Detect DST ambiguity / non-existence for a local date+time.

    This is a best-effort implementation using standard library `zoneinfo`.

    - Ambiguous: fold=0 and fold=1 map to different UTC instants.
    - Non-existent: roundtrip local->UTC->local does not preserve wall time.

    Note: There are edge cases where stdlib detection is conservative.
    """

    tz = get_zoneinfo(tz_id)

    dt0 = _aware_local(local_date, local_time, tz, fold=0)
    dt1 = _aware_local(local_date, local_time, tz, fold=1)

    utc0 = dt0.astimezone(UTC)
    utc1 = dt1.astimezone(UTC)
    ambiguous = utc0 != utc1

    # Non-existent times typically shift when you roundtrip.
    back0 = utc0.astimezone(tz)
    back1 = utc1.astimezone(tz)

    nonexistent = (
        (back0.replace(tzinfo=None) != dt0.replace(tzinfo=None))
        and (back1.replace(tzinfo=None) != dt1.replace(tzinfo=None))
    )

    return DstResolution(ambiguous=ambiguous, nonexistent=nonexistent)


def to_utc_instant(inp: LocalDateTimeInput) -> datetime:
    """Convert user-provided local date+time into a UTC instant.

    Implements Req 32 by validating DST ambiguity/non-existence.

    Policy:
    - If ambiguous, caller must choose fold (0/1).
    - If non-existent, raise ValidationError; caller may adjust input.
    """

    resolution = detect_dst_resolution(inp.local_date, inp.local_time, inp.tz_id)
    if resolution.nonexistent:
        raise ValidationError(
            "The provided local time does not exist in that time zone (DST transition)."
        )

    if resolution.ambiguous and inp.fold not in (0, 1):
        raise ValidationError("Fold must be 0 (earlier) or 1 (later) for ambiguous times.")

    tz = get_zoneinfo(inp.tz_id)
    local_dt = _aware_local(inp.local_date, inp.local_time, tz, fold=inp.fold)
    return local_dt.astimezone(UTC)


def format_dt(dt: datetime, time_format: str) -> str:
    """Format a timezone-aware datetime for display.

    Args:
        dt: A timezone-aware datetime.
        time_format: Either ``"24h"`` or ``"12h"``.

    Returns:
        A human-readable string including the time zone abbreviation.
    """

    if time_format == "12h":
        return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
