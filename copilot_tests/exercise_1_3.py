"""
exercise_1_3.py
---------------
Converts dates entered by the user to ISO 8601 format (YYYY-MM-DD).

Supported input conventions
----------------------------
  European : DD/MM/YYYY  (e.g. 28/02/2026)
  US       : MM/DD/YYYY  (e.g. 02/28/2026)

The user is asked once at startup which convention to use.
Type 'quit' at any prompt to exit the program.
"""

from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration: maps a short key to (display label, strptime format string,
# example string shown in error messages).
# Adding a new locale only requires a new entry here – no other code changes.
# ---------------------------------------------------------------------------
DATE_FORMATS: dict[str, tuple[str, str, str]] = {
    "eu": ("European (DD/MM/YYYY)", "%d/%m/%Y", "28/02/2026"),
    "us": ("US       (MM/DD/YYYY)", "%m/%d/%Y", "02/28/2026"),
}


def convert_to_iso(date_str: str, fmt: str) -> str:
    """Parse *date_str* using *fmt* and return the date as an ISO 8601 string.

    Parameters
    ----------
    date_str : str
        Raw date string supplied by the user (whitespace is stripped).
    fmt : str
        A :mod:`datetime` format string, e.g. ``"%d/%m/%Y"``.

    Returns
    -------
    str
        The date formatted as ``YYYY-MM-DD``.

    Raises
    ------
    ValueError
        Re-raised from :func:`datetime.strptime` with the original message
        intact so the caller can distinguish format errors from calendar
        errors.
    """
    return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")


def classify_error(exc: ValueError) -> str:
    """Return a human-readable error category from a :class:`ValueError`.

    :func:`datetime.strptime` raises ``ValueError`` for two distinct reasons:

    * **Format mismatch** – the string does not match the expected pattern
      (Python message contains ``"does not match format"`` or
      ``"unconverted data remains"``).
    * **Invalid calendar date** – the format matched but the date does not
      exist (e.g. 30 February).

    Parameters
    ----------
    exc : ValueError
        The exception raised by :func:`datetime.strptime`.

    Returns
    -------
    str
        Either ``"format"`` or ``"date"``.
    """
    msg = str(exc)
    if "does not match format" in msg or "unconverted data remains" in msg:
        return "format"
    return "date"


def select_format() -> tuple[str, str, str]:
    """Prompt the user to choose a date convention and return its details.

    Loops until a valid choice (``eu`` or ``us``) is entered.

    Returns
    -------
    tuple[str, str, str]
        ``(label, fmt, example)`` for the chosen convention.
    """
    print("Available date conventions:")
    for key, (label, _, _) in DATE_FORMATS.items():
        print(f"  {key.upper()}  –  {label}")

    while True:
        choice = input("\nSelect convention (EU / US): ").strip().lower()
        if choice in DATE_FORMATS:
            return DATE_FORMATS[choice]
        print(f"  Unknown option '{choice}'. Please enter EU or US.")


def main() -> None:
    """Entry point: selects a date convention then runs the conversion loop."""
    print("=" * 50)
    print("  Date Converter  →  ISO 8601 (YYYY-MM-DD)")
    print("=" * 50)
    print()

    label, fmt, example = select_format()
    print(f"\nUsing {label.strip()}")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("Enter date: ").strip()

        if user_input.lower() == "quit":
            print("Goodbye.")
            break

        try:
            iso_date = convert_to_iso(user_input, fmt)
            print(f"  ISO date : {iso_date}\n")
        except ValueError as exc:
            if classify_error(exc) == "format":
                print(
                    f"  Format error: '{user_input}' does not match the expected "
                    f"pattern.  Please use {label.strip()} – e.g. {example}\n"
                )
            else:
                print(
                    f"  Invalid date: '{user_input}' does not exist in the calendar "
                    f"(check day/month values).\n"
                )


if __name__ == "__main__":
    main()
