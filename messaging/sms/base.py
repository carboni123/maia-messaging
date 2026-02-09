"""Base protocol for SMS providers."""

from __future__ import annotations

from typing import Protocol

from messaging.types import DeliveryResult, SMSMessage


class SMSProvider(Protocol):
    """Interface that all SMS providers must implement."""

    def send(self, message: SMSMessage) -> DeliveryResult:
        """Send an SMS and return the delivery result."""
        ...

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Fetch current delivery status for a previously sent message.

        Returns None if the provider doesn't support status polling or
        the message is not found.
        """
        ...
