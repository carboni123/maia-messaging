"""Base protocol for messaging providers."""

from __future__ import annotations

from typing import Protocol

from messaging.types import DeliveryResult, Message


class MessagingProvider(Protocol):
    """Interface that all messaging providers must implement."""

    def send(self, message: Message) -> DeliveryResult:
        """Send a message and return the delivery result."""
        ...

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Fetch current delivery status for a previously sent message.

        Returns None if the provider doesn't support status polling or
        the message is not found.
        """
        ...
