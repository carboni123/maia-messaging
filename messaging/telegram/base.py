"""Base protocol for Telegram providers."""

from __future__ import annotations

from typing import Protocol, Union

from messaging.types import DeliveryResult, TelegramMedia, TelegramText

# Defined here (not in types.py) because Telegram messages use chat_id (int | str)
# rather than phone-based `to` fields, making them a separate message family.
TelegramMessage = Union[TelegramText, TelegramMedia]


class TelegramProvider(Protocol):
    """Interface that all Telegram providers must implement.

    Unlike MessagingProvider and SMSProvider, this protocol does not include
    fetch_status() because the Telegram Bot API is synchronous — a successful
    sendMessage call means the message was delivered. There is no async
    delivery pipeline to poll.
    """

    def send(self, message: TelegramMessage) -> DeliveryResult:
        """Send a Telegram message and return the delivery result."""
        ...

    async def send_async(self, message: TelegramMessage) -> DeliveryResult:
        """Send a Telegram message asynchronously."""
        ...
