"""Messaging providers.

Concrete providers must be imported from their module to keep
third-party SDK dependencies optional::

    from messaging.providers.meta import MetaWhatsAppProvider         # httpx (always available)
    from messaging.providers.whatsapp_personal import WhatsAppPersonalProvider  # httpx (always available)
    from messaging.providers.twilio import TwilioProvider             # requires `maia-messaging[twilio]`
"""

from .base import MessagingProvider
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

__all__ = [
    "MessagingProvider",
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
