"""Core types for the messaging gateway library."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class DeliveryStatus(str, Enum):
    """Status of a message delivery attempt."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    UNDELIVERED = "undelivered"

    @property
    def precedence(self) -> int:
        """Numeric precedence for status comparison.

        Higher values indicate more advanced delivery states.
        Negative values indicate terminal failure states.

        Matches the ``STATUS_PRECEDENCE`` map used in the app's
        ``CommunicationLog`` model so the library can be the source
        of truth for delivery status ordering.
        """
        return _STATUS_PRECEDENCE[self]


_STATUS_PRECEDENCE: dict[DeliveryStatus, int] = {
    DeliveryStatus.QUEUED: 1,
    DeliveryStatus.SENT: 4,
    DeliveryStatus.DELIVERED: 5,
    DeliveryStatus.READ: 6,
    DeliveryStatus.FAILED: -1,
    DeliveryStatus.UNDELIVERED: -2,
}


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Result of a single message delivery attempt from a provider."""

    status: DeliveryStatus
    external_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status not in {DeliveryStatus.FAILED, DeliveryStatus.UNDELIVERED}

    @classmethod
    def ok(
        cls,
        *,
        status: DeliveryStatus = DeliveryStatus.SENT,
        external_id: str | None = None,
    ) -> DeliveryResult:
        return cls(status=status, external_id=external_id)

    @classmethod
    def fail(
        cls,
        error_message: str,
        *,
        error_code: str | None = None,
    ) -> DeliveryResult:
        return cls(
            status=DeliveryStatus.FAILED,
            error_message=error_message,
            error_code=error_code,
        )


@dataclass(frozen=True, slots=True)
class GatewayResult:
    """Result from the MessagingGateway, wrapping DeliveryResult with gateway-level metadata."""

    delivery: DeliveryResult
    used_fallback_number: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.delivery.succeeded

    @property
    def status(self) -> DeliveryStatus:
        return self.delivery.status

    @property
    def external_id(self) -> str | None:
        return self.delivery.external_id

    @property
    def error_code(self) -> str | None:
        return self.delivery.error_code

    @property
    def error_message(self) -> str | None:
        return self.delivery.error_message


# ── Message types ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WhatsAppText:
    """A plain text WhatsApp message."""

    to: str
    body: str


@dataclass(frozen=True, slots=True)
class WhatsAppMedia:
    """A WhatsApp message with media attachments."""

    to: str
    media_urls: list[str] = field(default_factory=list)
    media_types: list[str] = field(default_factory=list)
    media_filenames: list[str] = field(default_factory=list)
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppTemplate:
    """A WhatsApp template message sent via Twilio Content API."""

    to: str
    content_sid: str
    content_variables: dict[str, str] = field(default_factory=dict)


Message = Union[WhatsAppText, WhatsAppMedia, WhatsAppTemplate]


# ── Provider configuration ────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TwilioConfig:
    """Configuration for creating a Twilio provider."""

    account_sid: str
    auth_token: str
    whatsapp_number: str  # Must be formatted as whatsapp:+E.164
    status_callback: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppPersonalConfig:
    """Configuration for creating a WhatsApp Personal provider."""

    session_public_id: str
    api_key: str
    adapter_base_url: str
