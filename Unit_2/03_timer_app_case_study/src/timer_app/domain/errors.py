"""Domain-specific exception types.

This module defines a small exception hierarchy that the domain and application
layers use to communicate user-facing failures (validation, missing entities)
and infrastructure failures (persistence).
"""

class TimerAppError(Exception):
    """Base exception for the timer app."""


class ValidationError(TimerAppError):
    """Raised when a user-facing input is invalid."""


class NotFoundError(TimerAppError):
    """Raised when an entity cannot be found."""


class StorageError(TimerAppError):
    """Raised when persistence fails."""
