# Code Review — `exercise_3a.py`

**Reviewer:** review-agent2 (Senior Software Engineer)  
**Date:** 2026-03-02  
**File:** `copilot_tests/exercise_3a.py`

---

## Code Under Review

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

1. Inspect imports for completeness and correctness.
2. Analyse `date_to_calendar_week` — signature, correctness, Python-version compatibility.
3. Analyse `add_days_to_date` — naming, validation, edge cases.
4. Assess cross-cutting concerns: type hints, docstrings, error handling, testability, style.

---

## Findings

### 1. Code Quality

- 🔴 **CRITICAL — Missing type hints on all parameters and return values.**  
  Neither function declares what types it accepts or returns. This makes the API contract invisible to callers and disables static analysis (mypy, Pylance).  
  - Fix: Add `date: datetime.date` and `-> int` / `-> datetime.date` annotations (see improved version below).

- 🟡 **WARNING — Poor parameter name `n` in `add_days_to_date`.**  
  Single-letter names carry no semantic meaning. A reader cannot tell whether `n` is days, hours, or some other unit without reading the body.  
  - Fix: Rename to `days` or `num_days`.

- 🟡 **WARNING — Parameter name `date` shadows the built-in `datetime.date` type.**  
  Inside both functions, using `date` as a variable name hides the type name, preventing its use for isinstance checks or annotations within the function body.  
  - Fix: Rename to `d` or keep `date` but import the type as `import datetime` and qualify it as `datetime.date`.

---

### 2. Correctness

- 🟡 **WARNING — `isocalendar()[1]` uses positional indexing on the ISO calendar tuple.**  
  In Python ≥ 3.9, `date.isocalendar()` returns an `IsoCalendarDate` named tuple. Using `.week` is clearer and more robust. In Python 3.8 and earlier, only index access is available, so this is a compatibility trade-off.  
  - Fix: Use `date.isocalendar().week` when targeting Python ≥ 3.9, or add a version guard / comment explaining the choice.

- 🟡 **WARNING — No validation of inputs.**  
  Both functions will raise a bare `AttributeError` or `TypeError` if passed `None` or a non-date object. The error message will not explain the expected type.  
  - Fix: Add a `isinstance` guard and raise a descriptive `TypeError` (see improved version).

- 🟢 **SUGGESTION — `n` (days) can be negative, which subtracts days.**  
  This is not necessarily wrong, but has no documentation. A caller wanting to subtract days might not realise it is supported, or might pass an unexpected float.  
  - Fix: Document in the docstring that negative values subtract days, and consider enforcing `int` type.

---

### 3. Security

- 🟢 **SUGGESTION — Both functions are pure utility functions with no I/O or external state exposure.**  
  No security concerns identified. If these functions are ever exposed via an API endpoint, standard input-type validation (already recommended above) would cover any risk.

---

### 4. Performance

- 🟢 **SUGGESTION — Both operations are O(1) and create no unnecessary objects.**  
  No performance issues identified.

---

### 5. Style & Code Conventions

- 🟡 **WARNING — Only one blank line separates the two top-level functions.**  
  [PEP 8](https://peps.python.org/pep-0008/#blank-lines) requires **two** blank lines between top-level definitions.  
  - Fix: Add a second blank line between `date_to_calendar_week` and `add_days_to_date`.

- 🟡 **WARNING — The inline comment `# Add n days to a date.` is not a docstring.**  
  Inline comments above a function definition are not part of `__doc__` and are invisible to help systems, IDEs, and documentation generators.  
  - Fix: Replace with a proper docstring inside the function body.

---

### 6. Readability & Maintainability

- 🔴 **CRITICAL — No docstrings on either function.**  
  Without docstrings, the contract of each function (expected types, return value, side effects, exceptions raised) is completely undocumented.  
  - Fix: Add Google-style or NumPy-style docstrings.

- 🟢 **SUGGESTION — No module-level docstring.**  
  A brief description of the module's purpose (date utility helpers) would help maintainers understand the file's scope at a glance.  
  - Fix: Add a module-level docstring at the top of the file.

---

### 7. Error Handling & Resilience

- 🟡 **WARNING — Silent failures on wrong types.**  
  Passing `None` to `date_to_calendar_week` raises `AttributeError: 'NoneType' object has no attribute 'isocalendar'` — an unhelpful message that does not guide the caller.  
  - Fix: Validate inputs explicitly with a `TypeError` that names the expected type.

- 🟢 **SUGGESTION — `timedelta(days=n)` will raise a `TypeError` if `n` is not numeric, but will silently accept floats.**  
  `timedelta` truncates fractional days; passing `1.9` silently gives a result identical to passing `1`. Consider restricting `n` to `int`.  
  - Fix: Add `if not isinstance(days, int): raise TypeError(...)`.

---

### 8. Testability & Test Coverage

- 🟢 **SUGGESTION — Both functions are pure (no side effects, no I/O), which is excellent for testability.**  
  However, no test file accompanies this module.  
  - Fix: Create `test_exercise_3a.py` covering at minimum:
    - `date_to_calendar_week`: first week of year, last week of year, a mid-year date, a year-boundary ISO-week date (e.g., 2024-12-30 is ISO week 1 of 2025).
    - `add_days_to_date`: positive days, zero days, negative days, month/year boundary crossing, leap-year boundary.

---

### 9. Architecture & Design

- 🟢 **SUGGESTION — `timedelta` is imported but `datetime.date` is not.**  
  The functions accept `datetime.date` objects but do not import the type. This is harmless at runtime but makes the type annotation story incomplete.  
  - Fix: Add `from datetime import date, timedelta` and annotate parameters accordingly.

- 🟢 **SUGGESTION — The two functions form a sensible date-utilities module.**  
  As the module grows, consider grouping related helpers (e.g., week calculations, day arithmetic) into a `DateUtils` class or a dedicated `date_utils.py` module.

---

### 10. Documentation

- 🔴 **CRITICAL — Both public functions lack docstrings (see §6).**
- 🟢 **SUGGESTION — No module-level docstring explaining the module's purpose (see §6).**

---

## Summary

| Category | Severity | Count |
|---|---|---|
| Code Quality | 🔴 CRITICAL / 🟡 WARNING | 3 |
| Correctness | 🟡 WARNING / 🟢 SUGGESTION | 3 |
| Security | 🟢 SUGGESTION | 1 |
| Performance | 🟢 SUGGESTION | 1 |
| Style | 🟡 WARNING | 2 |
| Readability | 🔴 CRITICAL / 🟢 SUGGESTION | 2 |
| Error Handling | 🟡 WARNING / 🟢 SUGGESTION | 2 |
| Testability | 🟢 SUGGESTION | 1 |
| Architecture | 🟢 SUGGESTION | 2 |
| Documentation | 🔴 CRITICAL / 🟢 SUGGESTION | 2 |

**Blockers (🔴 CRITICAL):** 3 — Missing type hints, missing docstrings (×2).

---

## Improved Version

```python
"""
date_utils.py
-------------
Utility functions for common date arithmetic and calendar calculations.
"""

from datetime import date, timedelta


def date_to_calendar_week(d: date) -> int:
    """Return the ISO 8601 calendar week number for the given date.

    Args:
        d: A :class:`datetime.date` instance.

    Returns:
        Integer week number in the range 1–53.

    Raises:
        TypeError: If *d* is not a :class:`datetime.date` instance.

    Example:
        >>> from datetime import date
        >>> date_to_calendar_week(date(2026, 3, 2))
        10
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date instance, got {type(d).__name__!r}.")
    return d.isocalendar().week  # Named attribute available in Python >= 3.9


def add_days_to_date(d: date, days: int) -> date:
    """Return a new date that is *days* days after (or before) *d*.

    Args:
        d: A :class:`datetime.date` instance representing the start date.
        days: Number of days to add. Use a negative value to subtract days.

    Returns:
        A new :class:`datetime.date` object.

    Raises:
        TypeError: If *d* is not a :class:`datetime.date` instance, or
                   if *days* is not an :class:`int`.

    Example:
        >>> from datetime import date
        >>> add_days_to_date(date(2026, 3, 2), 10)
        datetime.date(2026, 3, 12)
        >>> add_days_to_date(date(2026, 3, 2), -5)
        datetime.date(2026, 2, 25)
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected a datetime.date instance, got {type(d).__name__!r}.")
    if not isinstance(days, int):
        raise TypeError(f"Expected an int for 'days', got {type(days).__name__!r}.")
    return d + timedelta(days=days)
```

### Key improvements

| Change | Rationale |
|---|---|
| Module-level docstring | Documents the purpose of the file |
| `from datetime import date, timedelta` | Imports the `date` type for annotations and isinstance checks |
| `d: date` and `days: int` parameter types | Enables static analysis and makes the API contract explicit |
| `-> int` and `-> date` return types | Completes the type annotation |
| `isinstance` guards with descriptive `TypeError` | Fails fast with a clear error message instead of a confusing `AttributeError` |
| Renamed `date` → `d`, `n` → `days` | Avoids shadowing the imported type; `days` is self-documenting |
| `.isocalendar().week` instead of `[1]` | Uses the named attribute (Python ≥ 3.9) for clarity |
| Full Google-style docstrings on both functions | Documents contract, args, returns, raises, and usage examples |
| Two blank lines between top-level functions | Complies with PEP 8 |
