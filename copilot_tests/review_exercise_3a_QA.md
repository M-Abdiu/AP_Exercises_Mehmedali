# Code Review: exercise_3a.py

## Original Code

```python
from datetime import timedelta

def date_to_calendar_week(date):
    return date.isocalendar()[1]

# Add n days to a date.
def add_days_to_date(date, n):
    return date + timedelta(days=n)
```

---

## Review Findings

### Issues

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | **High** | Module level | `date` / `datetime` type is never imported. The functions operate on `datetime.date` objects, but the module only imports `timedelta`. This leaves the type unimported and makes the intent unclear. |
| 2 | **Medium** | `date_to_calendar_week` | Uses index-based tuple access `isocalendar()[1]`. Since Python 3.9, `isocalendar()` returns a named tuple (`IsoCalendarDate`), so `.week` should be preferred for clarity and future-proofing. |
| 3 | **Medium** | Both functions | No type hints. Without annotations it is not obvious that `date` must be a `datetime.date` instance and `n` must be an integer. |
| 4 | **Medium** | Both functions | No docstrings. There is no description of parameters, return values, or raised exceptions. The inline comment on `add_days_to_date` (`# Add n days to a date.`) partially compensates but is not sufficient. |
| 5 | **Low** | `add_days_to_date` | Parameter name `n` is not descriptive. A name like `days` or `num_days` clearly communicates intent. |
| 6 | **Low** | Both functions | No input validation. Passing a non-date object or a non-integer will raise a cryptic `AttributeError` or `TypeError` at runtime rather than a helpful message. |
| 7 | **Low** | Module level | No module-level docstring explaining the purpose of the module. |

### Positive Aspects

- Functions are small, single-purpose, and easy to understand.
- `timedelta` is used correctly for date arithmetic.
- The existing inline comment gives a minimal hint about intent.

---

## Improved Version

```python
"""
Utility functions for common date operations.
"""

from datetime import date, timedelta


def date_to_calendar_week(d: date) -> int:
    """Return the ISO calendar week number for the given date.

    Args:
        d: A datetime.date instance.

    Returns:
        The ISO week number (1–53).

    Raises:
        TypeError: If *d* is not a datetime.date instance.

    Example:
        >>> from datetime import date
        >>> date_to_calendar_week(date(2026, 2, 28))
        9
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date, got {type(d).__name__!r}")
    return d.isocalendar().week  # Named attribute available since Python 3.9


def add_days_to_date(d: date, days: int) -> date:
    """Return a new date that is *days* days after *d*.

    Args:
        d:    A datetime.date instance representing the start date.
        days: Number of days to add (may be negative to go backwards).

    Returns:
        A new datetime.date instance.

    Raises:
        TypeError: If *d* is not a datetime.date or *days* is not an int.

    Example:
        >>> from datetime import date
        >>> add_days_to_date(date(2026, 2, 28), 5)
        datetime.date(2026, 3, 5)
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date, got {type(d).__name__!r}")
    if not isinstance(days, int):
        raise TypeError(f"Expected an int for 'days', got {type(days).__name__!r}")
    return d + timedelta(days=days)
```

### Summary of Improvements

1. **Added module-level docstring** — communicates the purpose of the module at a glance.
2. **Imported `date`** — the type the functions actually work with is now explicitly available.
3. **Renamed parameters** — `date` → `d` (avoids shadowing the imported `date` type) and `n` → `days` (self-documenting).
4. **Added type hints** — `d: date`, `days: int`, `-> int` / `-> date` make the contract explicit for both readers and type-checkers (mypy, pyright).
5. **Added docstrings** — each function now documents its arguments, return value, exceptions, and includes a usage example.
6. **Used named attribute** — `isocalendar().week` instead of `isocalendar()[1]`, leveraging the `IsoCalendarDate` named tuple (Python ≥ 3.9).
7. **Added input validation** — both functions raise a descriptive `TypeError` when given unexpected argument types, making debugging easier.
