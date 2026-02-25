"""Small date utilities.

These helpers are intentionally minimal and rely on Python's standard
`datetime` types.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from datetime import timedelta

def date_to_calendar_week(value: Date | DateTime) -> int:
    """Return the ISO-8601 calendar week number for a given date/datetime."""

    if not hasattr(value, "isocalendar"):
        raise TypeError(
            "value must be a datetime.date or datetime.datetime (supports .isocalendar())"
        )

    # isocalendar() returns (ISO year, ISO week number, ISO weekday)
    return value.isocalendar()[1]

def add_days_to_date(value: Date | DateTime, days: int) -> Date | DateTime:
    """Add a number of days to a date/datetime and return the shifted value."""

    if not isinstance(days, int):
        raise TypeError("days must be an int")

    try:
        return value + timedelta(days=days)
    except TypeError as exc:
        raise TypeError(
            "value must be a datetime.date or datetime.datetime (supports date arithmetic)"
        ) from exc