"""Core types for the messaging gateway library."""

from __future__ import annotations

__all__ = [
    "DeliveryResult",
    "DeliveryStatus",
    "EmailMessage",
    "GatewayResult",
    "Message",
    "MetaWhatsAppConfig",
    "MetaWhatsAppTemplate",
    "SMSMessage",
    "SendGridConfig",
    "Smtp2GoConfig",
    "TelegramConfig",
    "TelegramMedia",
    "TelegramText",
    "TwilioConfig",
    "TwilioSMSConfig",
    "WhatsAppInteractiveCTA",
    "WhatsAppInteractiveList",
    "WhatsAppInteractiveReply",
    "WhatsAppMedia",
    "WhatsAppPersonalConfig",
    "WhatsAppProduct",
    "WhatsAppProductList",
    "WhatsAppTemplate",
    "WhatsAppText",
]

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
        Consuming apps can use this as the source of truth for
        delivery status ordering.
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


@dataclass(frozen=True, slots=True)
class MetaWhatsAppTemplate:
    """A WhatsApp template message sent via Meta Cloud API."""

    to: str
    template_name: str
    language_code: str  # e.g. "en_US", "pt_BR"
    components: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WhatsAppInteractiveReply:
    """A WhatsApp interactive reply-button message (session-only, no template needed).

    Up to 3 buttons. Each button has an ``id`` (callback payload) and
    ``title`` (label shown to the user, max 20 chars).

    Only supported on Meta Cloud API within the 24-hour session window.
    """

    to: str
    body: str
    buttons: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WhatsAppInteractiveList:
    """A WhatsApp interactive list message (Meta Cloud API, session-only).

    Presents a menu button that expands into sections with selectable rows.
    Up to 10 rows total across all sections. Each row has an ``id`` and
    ``title`` (max 24 chars), with an optional ``description`` (max 72 chars).

    ``button`` is the menu trigger text (max 20 chars).
    """

    to: str
    body: str
    button: str
    sections: list[dict[str, Any]]
    header: str | None = None
    footer: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppInteractiveCTA:
    """A WhatsApp interactive call-to-action URL button (Meta Cloud API, session-only).

    Shows a message with a tappable button that opens a URL.
    """

    to: str
    body: str
    display_text: str
    url: str
    header: str | None = None
    footer: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppProduct:
    """A WhatsApp single product message (Meta Cloud API, session-only).

    Displays a product from a connected Meta catalog.
    """

    to: str
    body: str
    catalog_id: str
    product_retailer_id: str
    footer: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppProductList:
    """A WhatsApp product list message (Meta Cloud API, session-only).

    Displays multiple products from a connected Meta catalog,
    organized in sections. Requires a header.
    """

    to: str
    body: str
    header: str
    catalog_id: str
    sections: list[dict[str, Any]]
    footer: str | None = None


Message = (
    WhatsAppText
    | WhatsAppMedia
    | WhatsAppTemplate
    | MetaWhatsAppTemplate
    | WhatsAppInteractiveReply
    | WhatsAppInteractiveList
    | WhatsAppInteractiveCTA
    | WhatsAppProduct
    | WhatsAppProductList
)


# ── Email message types ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """An email message."""

    to: str
    subject: str
    html_content: str
    from_email: str
    from_name: str = ""


# ── SMS message types ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SMSMessage:
    """A plain text SMS message."""

    to: str  # E.164 format, e.g. "+5511999999999"
    body: str


# ── Provider configuration ────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TwilioConfig:
    """Configuration for Twilio services (messaging, Content API).

    ``whatsapp_number`` is required for sending messages via ``TwilioProvider``
    but not needed for ``TwilioContentAPI`` template management.
    """

    account_sid: str
    auth_token: str
    whatsapp_number: str = ""  # Must be formatted as whatsapp:+E.164 for message delivery
    status_callback: str | None = None


@dataclass(frozen=True, slots=True)
class WhatsAppPersonalConfig:
    """Configuration for creating a WhatsApp Personal provider."""

    session_public_id: str
    api_key: str
    adapter_base_url: str


@dataclass(frozen=True, slots=True)
class MetaWhatsAppConfig:
    """Configuration for the Meta WhatsApp Cloud API provider."""

    phone_number_id: str
    access_token: str
    api_version: str = "v21.0"


@dataclass(frozen=True, slots=True)
class SendGridConfig:
    """Configuration for creating a SendGrid email provider."""

    api_key: str


@dataclass(frozen=True, slots=True)
class Smtp2GoConfig:
    """Configuration for creating an SMTP2GO email provider."""

    api_key: str


@dataclass(frozen=True, slots=True)
class TwilioSMSConfig:
    """Configuration for sending SMS via Twilio."""

    account_sid: str
    auth_token: str
    from_number: str  # E.164 format, e.g. "+14155238886"
    status_callback: str | None = None


# ── Telegram message types ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TelegramText:
    """A plain text Telegram message."""

    chat_id: str | int
    body: str
    parse_mode: str | None = None  # "HTML", "Markdown", or "MarkdownV2"


@dataclass(frozen=True, slots=True)
class TelegramMedia:
    """A Telegram message with a media attachment."""

    chat_id: str | int
    media_url: str
    media_type: str  # "photo", "document", "video"
    caption: str | None = None
    parse_mode: str | None = None


# ── Telegram provider configuration ─────────────────────────────────


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    """Configuration for the Telegram Bot API provider."""

    bot_token: str
