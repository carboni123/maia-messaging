"""Messaging providers."""

from .base import MessagingProvider
from .meta import MetaWhatsAppProvider
from .meta_schemas import (
    MetaErrorDetail,
    MetaErrorResponse,
    MetaMediaMessage,
    MetaMediaObject,
    MetaMessageContact,
    MetaMessageEntry,
    MetaMessageResponse,
    MetaTemplateComponentPayload,
    MetaTemplateLanguage,
    MetaTemplateMessage,
    MetaTemplateParameter,
    MetaTemplatePayload,
    MetaTextBody,
    MetaTextMessage,
)
from .twilio import TwilioProvider
from .whatsapp_personal import WhatsAppPersonalProvider

__all__ = [
    "MessagingProvider",
    "MetaWhatsAppProvider",
    "TwilioProvider",
    "WhatsAppPersonalProvider",
    # Meta WhatsApp API schemas
    "MetaErrorDetail",
    "MetaErrorResponse",
    "MetaMediaMessage",
    "MetaMediaObject",
    "MetaMessageContact",
    "MetaMessageEntry",
    "MetaMessageResponse",
    "MetaTemplateComponentPayload",
    "MetaTemplateLanguage",
    "MetaTemplateMessage",
    "MetaTemplateParameter",
    "MetaTemplatePayload",
    "MetaTextBody",
    "MetaTextMessage",
]
