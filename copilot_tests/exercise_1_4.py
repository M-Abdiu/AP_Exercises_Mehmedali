"""
exercise_1_4.py
---------------
Date format converter: converts dates in DD/MM/YYYY (European) or MM/DD/YYYY (US)
format to ISO 8601 standard (YYYY-MM-DD).

Features:
    - Supports European (DD/MM/YYYY) and US (MM/DD/YYYY) date formats
    - Validates input for empty values, wrong format, and invalid dates (incl. leap years)
    - Runs continuously until the user enters the sentinel value 'quit'
    - Follows the DRY principle via dedicated helper functions

Scope exclusions:
    - Timezones are not supported
    - 2-digit years are not supported

Usage:
    python exercise_1_4.py
"""

import datetime
import re

# ── Constants ──────────────────────────────────────────────────────────────────

SENTINEL: str = "quit"
"""Sentinel value that terminates the input loop."""

DATE_PATTERN: re.Pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")
"""Regex pattern that accepts exactly DD/MM/YYYY or MM/DD/YYYY (both share the same structure)."""

FORMAT_OPTIONS: dict[str, str] = {
    "eu": "European (DD/MM/YYYY)",
    "us": "US (MM/DD/YYYY)",
}
"""Supported format keys mapped to their human-readable labels."""

STRPTIME_FORMATS: dict[str, str] = {
    "eu": "%d/%m/%Y",
    "us": "%m/%d/%Y",
}
"""Mapping from format key to strptime format string."""


# ── Helper functions ───────────────────────────────────────────────────────────

def choose_date_format() -> str:
    """Prompt the user to select a date format and return the validated choice.

    Loops until the user enters a valid option ('eu' or 'us', case-insensitive).

    Returns:
        str: 'eu' for European format (DD/MM/YYYY) or 'us' for US format (MM/DD/YYYY).
    """
    while True:
        print("\nSelect date format:")
        for key, description in FORMAT_OPTIONS.items():
            print(f"  {key.upper()} – {description}")
        choice = input("Enter your choice (EU/US): ").strip().lower()
        if choice in FORMAT_OPTIONS:
            print(f"Using {FORMAT_OPTIONS[choice]} format.\n")
            return choice
        valid = ", ".join(k.upper() for k in FORMAT_OPTIONS)
        print(f"  Error: Invalid choice. Please enter one of: {valid}.")


def validate_format(date_str: str) -> None:
    """Check that *date_str* matches the two-digit/two-digit/four-digit pattern.

    Args:
        date_str (str): The raw date string provided by the user.

    Raises:
        ValueError: If *date_str* does not match ``DD/MM/YYYY`` / ``MM/DD/YYYY`` structure.
    """
    if not DATE_PATTERN.match(date_str):
        raise ValueError(
            f"Invalid format: '{date_str}'. "
            "Expected DD/MM/YYYY (EU) or MM/DD/YYYY (US) with 4-digit year."
        )


def parse_date(date_str: str, fmt: str) -> datetime.date:
    """Parse *date_str* according to *fmt* and return a :class:`datetime.date`.

    Uses :func:`datetime.datetime.strptime` which automatically validates day/month
    ranges and leap years (e.g. 29/02 is only valid in a leap year).

    Args:
        date_str (str): Date string that has already passed format validation.
        fmt (str): Format key – ``'eu'`` or ``'us'``.

    Returns:
        datetime.date: The parsed date.

    Raises:
        ValueError: If the date is logically invalid (e.g. month 13, day 30 in February).
    """
    try:
        return datetime.datetime.strptime(date_str, STRPTIME_FORMATS[fmt]).date()
    except ValueError:
        # Provide a more informative error message than the default strptime one.
        part1, part2, year = date_str.split("/")
        day, month = (part1, part2) if fmt == "eu" else (part2, part1)
        raise ValueError(
            f"Invalid date – day={day}, month={month}, year={year}. "
            "Check that the day/month values are in range and that leap year rules are respected."
        )


def to_iso(date: datetime.date) -> str:
    """Convert a :class:`datetime.date` to an ISO 8601 string (YYYY-MM-DD).

    Args:
        date (datetime.date): The date to format.

    Returns:
        str: ISO 8601 representation, e.g. ``'2026-02-01'``.
    """
    return date.isoformat()


def process_input(raw: str, fmt: str) -> str:
    """Validate, parse, and convert *raw* to an ISO 8601 date string.

    Centralises all validation steps so that callers only need to handle the
    single :class:`ValueError` that this function may raise.

    Args:
        raw (str): The (already stripped) user input.
        fmt (str): Format key – ``'eu'`` or ``'us'``.

    Returns:
        str: ISO 8601 date string.

    Raises:
        ValueError: On empty input, wrong format pattern, or invalid calendar date.
    """
    if not raw:
        raise ValueError("Input cannot be empty. Please enter a date or 'quit' to exit.")
    validate_format(raw)
    parsed = parse_date(raw, fmt)
    return to_iso(parsed)


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the interactive date-conversion loop.

    Workflow:
        1. Ask the user to pick EU or US format (once per session).
        2. Repeatedly prompt for a date, convert it, and print the ISO result.
        3. Stop when the user enters the sentinel value (``'quit'``).
    """
    print("=" * 52)
    print("       Date → ISO 8601 Converter")
    print("=" * 52)
    print(f"Type '{SENTINEL}' at any prompt to exit.\n")

    fmt = choose_date_format()
    format_label = FORMAT_OPTIONS[fmt]
    print(f"Ready. Enter dates in {format_label} format.")
    print("-" * 52)

    while True:
        raw = input("Date (or 'quit'): ").strip()

        if raw.lower() == SENTINEL:
            print("Goodbye!")
            break

        try:
            iso_date = process_input(raw, fmt)
            print(f"  → ISO 8601 : {iso_date}")
        except ValueError as exc:
            print(f"  Error: {exc}")


if __name__ == "__main__":
    main()
