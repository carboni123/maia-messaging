"""Shared Twilio helpers used by both WhatsApp and SMS providers."""

from __future__ import annotations

__all__ = ["map_twilio_status"]

import logging

from messaging.types import DeliveryStatus

logger = logging.getLogger(__name__)


def map_twilio_status(twilio_status: str | None) -> DeliveryStatus:
    """Map a Twilio message status string to our DeliveryStatus enum."""
    mapping: dict[str, DeliveryStatus] = {
        "queued": DeliveryStatus.QUEUED,
        "sent": DeliveryStatus.SENT,
        "delivered": DeliveryStatus.DELIVERED,
        "read": DeliveryStatus.READ,
        "failed": DeliveryStatus.FAILED,
        "undelivered": DeliveryStatus.UNDELIVERED,
        "accepted": DeliveryStatus.QUEUED,
        "sending": DeliveryStatus.QUEUED,
        "receiving": DeliveryStatus.QUEUED,
        "received": DeliveryStatus.DELIVERED,
        "scheduled": DeliveryStatus.QUEUED,
        "canceled": DeliveryStatus.FAILED,
    }
    if not twilio_status:
        return DeliveryStatus.QUEUED

    normalized_status = twilio_status.lower()
    if normalized_status in mapping:
        return mapping[normalized_status]

    logger.warning("Unknown Twilio message status received: %s", twilio_status)
    return DeliveryStatus.FAILED
