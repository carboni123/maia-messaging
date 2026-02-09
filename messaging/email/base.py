"""Base protocol for email providers."""

from __future__ import annotations

from typing import Protocol

from messaging.types import DeliveryResult, EmailMessage


class EmailProvider(Protocol):
    """Interface that all email providers must implement."""

    def send(self, message: EmailMessage) -> DeliveryResult:
        """Send an email and return the delivery result."""
        ...
