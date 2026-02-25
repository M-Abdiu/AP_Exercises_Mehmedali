"""Notification port interface.

Notifications represent user-visible alerts (e.g., alarm fired) without tying
the application to a specific UI framework.
"""

from __future__ import annotations

from typing import Protocol


class NotificationSink(Protocol):
    """A sink that can display or emit user notifications."""

    def notify(self, title: str, message: str) -> None:
        """Emit an in-app notification."""
