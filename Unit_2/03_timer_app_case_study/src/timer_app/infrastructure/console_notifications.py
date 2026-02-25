"""Console notification adapter.

This adapter implements :class:`timer_app.ports.notifications.NotificationSink`
by printing timestamped messages to stdout.
"""

from __future__ import annotations

from datetime import datetime

from timer_app.ports.notifications import NotificationSink


class ConsoleNotificationSink(NotificationSink):
    """Print notifications to stdout."""

    def notify(self, title: str, message: str) -> None:
        """Print a timestamped notification line."""
        ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        print(f"[{ts}] {title}: {message}")
