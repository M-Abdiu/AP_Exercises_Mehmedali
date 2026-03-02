# Code Review: exercise_3a.py

**Reviewer:** review-agent1  
**Date:** 2026-03-02  
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

## Summary Ratings

| Dimension | Rating |
|---|---|
| Quality | Needs Improvement |
| Maintainability | Needs Improvement |
| Security | Good |
| Robustness | Needs Improvement |
| Performance | Good |
| Documentation | Poor |
| Code Style | Needs Improvement |

---

## Detailed Findings

### 1. Quality — *Needs Improvement*

- 🟡 **WARNING: Index-based access on `isocalendar()` result.**  
  `date.isocalendar()[1]` relies on a positional index. Since Python 3.9, `isocalendar()` returns a named tuple (`IsoCalendarDate`) with attributes `.year`, `.week`, and `.weekday`. Using `.week` is clearer and less fragile.  
  - Fix: Replace `date.isocalendar()[1]` with `date.isocalendar().week`.

- 🟡 **WARNING: No type hints on either function.**  
  The expected types of `date` (a `datetime.date` object) and `n` (an `int`) are not declared, making the contract of each function ambiguous. Static analysis tools such as `mypy` cannot catch type mismatches at development time.  
  - Fix: Add annotations — `d: date`, `days: int`, `-> int`, `-> date`.

- 🟢 **SUGGESTION: Logic is otherwise correct.**  
  `timedelta(days=n)` correctly adds whole days to a date; the return value of `isocalendar()[1]` is the correct ISO week number.

---

### 2. Maintainability — *Needs Improvement*

- 🟡 **WARNING: Parameter name `date` shadows the `datetime.date` class.**  
  Using `date` as a parameter name masks the standard-library type of the same name if it is imported, and is easily confused with the `datetime.date` class. A single-letter or clearly distinct name (e.g. `d`) avoids the ambiguity.  
  - Fix: Rename the parameter to `d` in both functions.

- 🟡 **WARNING: Parameter `n` is not descriptive.**  
  The name `n` gives no indication of what the value represents. A caller reading a call such as `add_days_to_date(start, 7)` cannot infer the unit without reading the implementation.  
  - Fix: Rename `n` to `days` (or `num_days`).

- 🟢 **SUGGESTION: Redundant inline comment.**  
  The comment `# Add n days to a date.` repeats exactly what the function name already communicates and adds maintenance burden (it can drift from the implementation).  
  - Fix: Remove the inline comment; replace with a proper docstring.

---

### 3. Security — *Good*

- 🟢 **No security concerns** in these pure, stateless utility functions. There is no I/O, no subprocess usage, no serialization, and no exposure of sensitive data. If date strings originate from untrusted user input, validation should happen in the calling layer before these functions are invoked.

---

### 4. Robustness — *Needs Improvement*

- 🟡 **WARNING: No guard against `None` or wrong types for `date`/`d`.**  
  Passing `None` produces an uninformative `AttributeError: 'NoneType' object has no attribute 'isocalendar'`. Passing a plain string produces a similarly cryptic error. Callers receive no indication of the expected type.  
  - Fix: Add an `isinstance(d, date)` guard and raise `TypeError` with a descriptive message.

- 🟡 **WARNING: `n` / `days` is not validated.**  
  Passing a non-numeric value (e.g. `"7"`) causes `TypeError: unsupported type for timedelta days component` deep inside the standard library, with no context about which argument was at fault.  
  - Fix: Validate that `days` is an `int` at the start of the function with a clear error message.

- 🟢 **SUGGESTION: ISO week boundary behaviour is undocumented.**  
  Year-boundary dates (e.g. 2020-12-31) can return ISO week 53 or week 1 of the following year. This is correct ISO 8601 behaviour but may surprise callers. It should be noted in the docstring.

---

### 5. Performance — *Good*

- 🟢 Both functions are **O(1)** and use only built-in standard-library operations. No caching, batching, or algorithmic optimisations are needed at this scale.

---

### 6. Documentation — *Poor*

- 🔴 **CRITICAL: No docstrings on either function.**  
  Neither function has a docstring describing its purpose, parameters, return value, or possible exceptions. This makes the API opaque to users who rely on `help()`, IDE tooltips, or generated documentation.  
  - Fix: Add Google-style (or NumPy/reStructuredText) docstrings to both functions.

- 🟡 **WARNING: No module-level docstring.**  
  PEP 257 recommends a module docstring explaining the purpose and contents of the module.  
  - Fix: Add a one-line (or multi-line) module docstring.

- 🟢 **SUGGESTION: No usage examples.**  
  Including `doctest`-compatible examples in the docstrings would serve as both documentation and lightweight regression tests.

---

### 7. Code Style — *Needs Improvement*

- 🟡 **WARNING: Only one blank line between top-level function definitions.**  
  PEP 8 requires **two blank lines** before and after each top-level function. There is only one blank line between `date_to_calendar_week` and `add_days_to_date`.  
  - Fix: Add a second blank line between the two functions.

- 🟡 **WARNING: `datetime.date` is never imported.**  
  The module imports only `timedelta`. If type hints referencing `date` are added, the import must include `date` as well.  
  - Fix: Change `from datetime import timedelta` to `from datetime import date, timedelta`.

- 🟢 **SUGGESTION: No `if __name__ == "__main__":` guard.**  
  Adding a guard with a few example calls makes the module safe to import and provides a quick smoke-test.

---

## Improved Version

```python
"""
Utility functions for common date arithmetic and calendar calculations.

All functions expect standard :class:`datetime.date` instances as input.
Date strings from external sources should be parsed and validated before
being passed to these functions.
"""

from datetime import date, timedelta


def date_to_calendar_week(d: date) -> int:
    """Return the ISO 8601 calendar week number for the given date.

    Args:
        d: A :class:`datetime.date` instance.

    Returns:
        An integer in the range 1–53 representing the ISO week number.

    Raises:
        TypeError: If *d* is not a :class:`datetime.date` instance.

    Note:
        Dates near the end or beginning of a year may belong to the last
        week of the preceding year or the first week of the following year
        (ISO 8601 behaviour).

    Example:
        >>> from datetime import date
        >>> date_to_calendar_week(date(2026, 3, 2))
        10
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date, got {type(d).__name__!r}")
    return d.isocalendar().week  # Named attribute available since Python 3.9


def add_days_to_date(d: date, days: int) -> date:
    """Return a new date that is *days* days after *d*.

    Args:
        d:    A :class:`datetime.date` instance representing the start date.
        days: Number of days to add. Use a negative value to go backwards.

    Returns:
        A new :class:`datetime.date` instance offset by *days* days.

    Raises:
        TypeError: If *d* is not a :class:`datetime.date` instance, or if
                   *days* is not an integer.

    Example:
        >>> from datetime import date
        >>> add_days_to_date(date(2026, 3, 2), 7)
        datetime.date(2026, 3, 9)
        >>> add_days_to_date(date(2026, 3, 2), -1)
        datetime.date(2026, 3, 1)
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date, got {type(d).__name__!r}")
    if not isinstance(days, int):
        raise TypeError(f"Expected an int for 'days', got {type(days).__name__!r}")
    return d + timedelta(days=days)


if __name__ == "__main__":
    from datetime import date as _date

    sample = _date(2026, 3, 2)
    print(f"ISO week of {sample}: {date_to_calendar_week(sample)}")
    print(f"{sample} + 10 days: {add_days_to_date(sample, 10)}")
```
