"""Messaging gateway library for WhatsApp delivery."""

from .gateway import MessagingGateway
from .mock import MockProvider
from .phone import denormalize_phone_for_whatsapp, format_whatsapp_number, normalize_phone, normalize_whatsapp_id, phones_match
from .pricing import calculate_template_cost
from .providers.base import MessagingProvider
from .providers.twilio import TwilioProvider, empty_messaging_response_xml
from .providers.whatsapp_personal import WhatsAppPersonalProvider
from .types import (
    DeliveryResult,
    DeliveryStatus,
    GatewayResult,
    Message,
    TwilioConfig,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppTemplate,
    WhatsAppText,
)

__all__ = [
    # Gateway
    "MessagingGateway",
    # Providers
    "MessagingProvider",
    "TwilioProvider",
    "WhatsAppPersonalProvider",
    "MockProvider",
    "empty_messaging_response_xml",
    # Types
    "DeliveryResult",
    "DeliveryStatus",
    "GatewayResult",
    "Message",
    "TwilioConfig",
    "WhatsAppMedia",
    "WhatsAppPersonalConfig",
    "WhatsAppTemplate",
    "WhatsAppText",
    # Phone
    "denormalize_phone_for_whatsapp",
    "format_whatsapp_number",
    "normalize_phone",
    "normalize_whatsapp_id",
    "phones_match",
    # Pricing
    "calculate_template_cost",
]
