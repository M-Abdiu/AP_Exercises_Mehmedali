# Code Review: exercise_3a.py

**Reviewer:** review-agent2  
**Date:** 2026-03-01  
**File:** `exercise_3a.py`

---

## Source Code Under Review

```python
from datetime import timedelta

def date_to_calendar_week(date):
    return date.isocalendar()[1]

# Add n days to a date.
def add_days_to_date(date, n):
    return date + timedelta(days=n)
```

---

## Review Plan

1. Analyze both utility functions for logic correctness and edge cases.
2. Assess code quality: naming, type hints, docstrings, PEP 8 compliance.
3. Evaluate security: input validation, unexpected inputs.
4. Check performance: algorithmic efficiency.
5. Review style conventions: spacing, idiomatic Python usage.
6. Assess readability, maintainability, and documentation.
7. Check error handling and resilience.
8. Evaluate testability and note missing test scenarios.
9. Assess architecture and design choices.
10. Produce an improved version of the code.

---

## Review Findings

### Code Quality

-  WARNING: **No type hints on either function.**  
  Both `date_to_calendar_week` and `add_days_to_date` accept parameters (`date`, `n`) without any type annotations. This makes it ambiguous whether `date` is a `datetime.date`, `datetime.datetime`, or something else, and whether `n` is `int` or `float`. IDEs and static analysis tools (mypy) cannot catch type mismatches.
  - Fix: Add type hints  `date: datetime.date`, `n: int`, return `-> int` and `-> datetime.date` respectively.

-  SUGGESTION: **Magic index `[1]` in `isocalendar()`.**  
  `.isocalendar()[1]` uses a positional index that is not self-explanatory. Since Python 3.9, `isocalendar()` returns a named tuple `IsoCalendarDate` with attributes `.year`, `.week`, `.weekday`.
  - Fix: Replace `date.isocalendar()[1]` with `date.isocalendar().week` for clarity and future-proofing.

-  SUGGESTION: **Redundant inline comment on `add_days_to_date`.**  
  The comment `# Add n days to a date.` duplicates exactly what the function name already communicates. It adds no value and creates maintenance burden (comment can drift from implementation).
  - Fix: Remove the inline comment; replace with a proper docstring if documentation is needed.

---

### Correctness

-  WARNING: **No guard against `None` or wrong types for `date`.**  
  If `None` is passed as `date`, both functions raise an uninformative `AttributeError` (`'NoneType' object has no attribute 'isocalendar'` / `unsupported operand type(s)`). The caller receives no indication of what went wrong.
  - Fix: Add an `isinstance` guard or raise a `TypeError` with a descriptive message, e.g. `if not isinstance(date, datetime.date): raise TypeError(...)`.

-  WARNING: **`n` is not validated in `add_days_to_date`.**  
  Passing a non-numeric value for `n` (e.g. a string) will cause `timedelta(days=n)` to raise a `TypeError` deep inside the standard library, with no context about which argument was wrong.
  - Fix: Validate `n` is an `int` (or accept `float` explicitly) at the top of the function with a clear error message.

-  SUGGESTION: **ISO week boundary edge cases are silently accepted.**  
  Year-boundary dates (e.g. 2020-12-31) can return ISO week 53 or week 1 of the next year. This is correct ISO 8601 behavior, but callers may be surprised. The behavior should be documented in a docstring.
  - Fix: Add a docstring noting ISO 8601 week semantics and the year-boundary behavior.

---

### Security

-  SUGGESTION: **No injection or secret risks** in these pure utility functions. However, if `date` values come from user input (e.g., a web form), callers should validate and parse the date string before passing it to these functions  this responsibility should be documented.
  - Fix: Note in the module/function docstring that inputs are expected to be pre-validated `datetime.date` objects.

---

### Performance

-  SUGGESTION: **No performance concerns.** Both functions are O(1) and use only standard library primitives. No caching, batching, or algorithmic improvements are needed at this scale.

---

### Style & Code Conventions

-  WARNING: **Missing blank lines between top-level definitions.**  
  PEP 8 requires **two blank lines** before and after top-level function definitions. The two functions are separated by only one blank line, and the first function has no blank lines between the import and its definition.
  - Fix: Add two blank lines before each `def` at module level.

-  SUGGESTION: **Missing module-level docstring.**  
  PEP 257 and common Python project conventions recommend a module-level docstring describing the purpose of the module.
  - Fix: Add a module docstring, e.g. `"""Utility functions for date arithmetic and calendar calculations."""`.

---

### Readability & Maintainability

-  CRITICAL: **No docstrings on either function.**  
  Neither function has a docstring. This means there is no documented API contract: what types are expected, what is returned, what exceptions may be raised, and what edge cases exist (e.g. ISO week 53). This is especially important for shared/library code.
  - Fix: Add Google-style or reStructuredText docstrings to both functions documenting `Args`, `Returns`, `Raises`, and notable edge cases.

-  SUGGESTION: **Parameter name `n` in `add_days_to_date` is too terse.**  
  `n` is a common placeholder name but not self-documenting. Within the context of date utilities, `num_days` or `days` would be clearer.
  - Fix: Rename `n` to `num_days` (or `days`) for clarity.

---

### Error Handling & Resilience

-  WARNING: **Silent failure on invalid input types.**  
  Both functions will raise Python built-in exceptions (`AttributeError`, `TypeError`) with no contextual error messages. For library functions, wrapping and re-raising with context improves debuggability.
  - Fix: Add explicit `isinstance` checks at entry and raise `TypeError` with a human-readable message before delegating to standard library calls.

---

### Testability & Test Coverage

-  WARNING: **No tests are present.**  
  The functions are pure and easily testable, but no test module exists. The following scenarios are untested:
  - `date_to_calendar_week`: week 1 (Jan 1 that belongs to the previous ISO year), week 53, leap year dates, year boundaries (e.g. 2020-12-31  week 53).
  - `add_days_to_date`: adding 0 days, negative days (subtraction), large values, leap year boundary (Feb 28/29), `None` input.
  - Fix: Create `test_exercise_3a.py` using `pytest` or `unittest` covering the above edge cases.

-  SUGGESTION: **Functions are pure and have no side effects**  this makes them straightforward to unit test without mocking. The design is good in this regard.

---

### Architecture & Design

-  SUGGESTION: **Good single-responsibility principle.** Each function does exactly one thing. No issues with coupling or cohesion at this scale.

-  SUGGESTION: **Consider grouping into a dedicated module.** If more date utilities exist (or are planned), these functions would benefit from a dedicated `date_utils.py` module with a clear public API, rather than living in an exercise file.

---

### Documentation

-  CRITICAL: **Zero documentation throughout the file.**  
  There is no module docstring, no function docstrings, and the only comment present is redundant. For any code meant to be maintained or shared, this is a significant gap.
  - Fix: Add a module docstring and docstrings for both functions as shown in the improved version below.

---

## Summary Table

| Category | Severity | Issue Count |
|---|---|---|
| Code Quality |  WARNING +  SUGGESTION | 2 |
| Correctness |  WARNING  2 +  SUGGESTION | 3 |
| Security |  SUGGESTION | 1 |
| Performance |  SUGGESTION | 1 |
| Style & Code Conventions |  WARNING +  SUGGESTION | 2 |
| Readability & Maintainability |  CRITICAL +  SUGGESTION | 2 |
| Error Handling & Resilience |  WARNING | 1 |
| Testability & Test Coverage |  WARNING +  SUGGESTION | 2 |
| Architecture & Design |  SUGGESTION  2 | 2 |
| Documentation |  CRITICAL | 1 |

**Total: 2 CRITICAL  5 WARNINGS  9 SUGGESTIONS**

---

## Improved Version

```python
"""Utility functions for date arithmetic and ISO calendar week calculations."""

from __future__ import annotations

import datetime


def date_to_calendar_week(date: datetime.date) -> int:
    """Return the ISO 8601 calendar week number for the given date.

    ISO 8601 weeks start on Monday. Week 1 is the week containing the first
    Thursday of the year. This means that dates near year boundaries may
    belong to week 52/53 of the previous year or week 1 of the next year.

    Args:
        date: A ``datetime.date`` (or ``datetime.datetime``) instance.

    Returns:
        An integer in the range 153 representing the ISO week number.

    Raises:
        TypeError: If ``date`` is not a ``datetime.date`` instance.

    Examples:
        >>> import datetime
        >>> date_to_calendar_week(datetime.date(2026, 3, 1))
        9
        >>> date_to_calendar_week(datetime.date(2020, 12, 31))  # ISO week 53
        53
    """
    if not isinstance(date, datetime.date):
        raise TypeError(
            f"Expected a datetime.date instance, got {type(date).__name__!r}."
        )
    return date.isocalendar().week


def add_days_to_date(date: datetime.date, num_days: int) -> datetime.date:
    """Return a new date that is ``num_days`` days after (or before) ``date``.

    Args:
        date: A ``datetime.date`` (or ``datetime.datetime``) instance.
        num_days: Number of days to add. Use a negative value to subtract days.

    Returns:
        A ``datetime.date`` (or ``datetime.datetime``) shifted by ``num_days``.

    Raises:
        TypeError: If ``date`` is not a ``datetime.date`` instance, or if
            ``num_days`` is not an integer.

    Examples:
        >>> import datetime
        >>> add_days_to_date(datetime.date(2026, 3, 1), 10)
        datetime.date(2026, 3, 11)
        >>> add_days_to_date(datetime.date(2026, 3, 1), -1)
        datetime.date(2026, 2, 28)
    """
    if not isinstance(date, datetime.date):
        raise TypeError(
            f"Expected a datetime.date instance for 'date', got {type(date).__name__!r}."
        )
    if not isinstance(num_days, int):
        raise TypeError(
            f"Expected an integer for 'num_days', got {type(num_days).__name__!r}."
        )
    return date + datetime.timedelta(days=num_days)
```

### Key Changes in the Improved Version

1. **Module docstring** added at the top.
2. **`from __future__ import annotations`** included for forward-compatible type hints.
3. **`datetime` imported as a module** (`import datetime`) instead of only `timedelta`  avoids namespace pollution and makes it explicit that `datetime.date` is used.
4. **Full type hints** on both functions (`date: datetime.date`, `num_days: int`, return types).
5. **Comprehensive docstrings** (Google-style) covering purpose, args, returns, raises, and examples.
6. **Input validation** with descriptive `TypeError` messages for both functions.
7. **`.isocalendar().week`** used instead of `.isocalendar()[1]`  named attribute, not positional index.
8. **`n` renamed to `num_days`**  self-documenting parameter name.
9. **Redundant inline comment removed**  replaced by the docstring.
10. **PEP 8 spacing**: two blank lines between top-level definitions.
