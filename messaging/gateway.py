"""Messaging gateway — the main entry point for sending messages.

The gateway wraps a provider with cross-cutting concerns like
phone number fallback for Brazilian numbers.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING

from .phone import denormalize_phone_for_whatsapp
from .types import DeliveryResult, DeliveryStatus, GatewayResult, MetaWhatsAppTemplate, WhatsAppMedia, WhatsAppTemplate, WhatsAppText

if TYPE_CHECKING:
    from .providers.base import MessagingProvider
    from .types import Message

logger = logging.getLogger(__name__)

# Error messages that indicate an invalid phone number format
_INVALID_NUMBER_INDICATORS = [
    "invalid number",
    "not a valid whatsapp",
    "number is not registered",
    "unregistered",
    "invalid 'to' phone number",
    "is not a whatsapp user",
]


class MessagingGateway:
    """Sends messages through a provider with optional phone fallback.

    Usage::

        from messaging import MessagingGateway, TwilioProvider, TwilioConfig, WhatsAppText

        provider = TwilioProvider(TwilioConfig(...))
        gateway = MessagingGateway(provider)
        result = gateway.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))
        if result.succeeded:
            print(f"Sent: {result.external_id}")
    """

    def __init__(self, provider: MessagingProvider) -> None:
        self.provider = provider

    def send(
        self,
        message: Message,
        *,
        phone_fallback: bool = False,
    ) -> GatewayResult:
        """Send a message, optionally retrying with alternate phone format.

        Args:
            message: The message to send.
            phone_fallback: If True, retry with denormalized Brazilian phone
                format when the first attempt fails with an invalid number error.

        Returns:
            GatewayResult wrapping the DeliveryResult and any fallback info.
        """
        result = self.provider.send(message)

        if phone_fallback and _is_invalid_number_error(result):
            to_number = _get_to(message)
            fallback_to = denormalize_phone_for_whatsapp(to_number)
            if fallback_to and fallback_to != to_number:
                logger.info(
                    "Retrying with fallback phone format: %s -> %s",
                    to_number,
                    fallback_to,
                )
                fallback_msg = _replace_to(message, fallback_to)
                fallback_result = self.provider.send(fallback_msg)
                if fallback_result.status != DeliveryStatus.FAILED:
                    return GatewayResult(
                        delivery=fallback_result,
                        used_fallback_number=fallback_to,
                    )

        return GatewayResult(delivery=result)

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Fetch delivery status for a previously sent message."""
        return self.provider.fetch_status(external_id)


def _is_invalid_number_error(result: DeliveryResult) -> bool:
    """Check if a delivery failure indicates an invalid phone number."""
    if result.status != DeliveryStatus.FAILED:
        return False
    error_str = (result.error_message or "").lower()
    return any(indicator in error_str for indicator in _INVALID_NUMBER_INDICATORS)


def _get_to(message: Message) -> str:
    """Extract the 'to' field from any message type."""
    return message.to  # All message types have a 'to' field


def _replace_to(message: Message, new_to: str) -> Message:
    """Create a copy of the message with a different 'to' number."""
    if isinstance(message, (WhatsAppText, WhatsAppMedia, WhatsAppTemplate, MetaWhatsAppTemplate)):
        return dataclasses.replace(message, to=new_to)
    return message  # Unreachable for known types
