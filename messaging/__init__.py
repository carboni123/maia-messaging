"""maia-messaging — Multi-channel messaging delivery library.

Standalone messaging gateway extracted from the Meu Assistente IA backend.
Owns everything from "I have a resolved message and provider config" to
"here's what happened." The consuming app retains orchestration (who to send
to, which provider account, quota, logging).

Installation
------------

Base install (Meta WhatsApp, WhatsApp Personal adapter, SMTP2GO, Telegram,
phone utils — everything that runs on ``httpx``)::

    pip install maia-messaging@git+https://github.com/carboni123/maia-messaging.git

With Twilio support (WhatsApp + SMS + Content API templates)::

    pip install "maia-messaging[twilio]@git+https://github.com/carboni123/maia-messaging.git"

With SendGrid email support::

    pip install "maia-messaging[sendgrid]@git+https://github.com/carboni123/maia-messaging.git"

Everything::

    pip install "maia-messaging[all]@git+https://github.com/carboni123/maia-messaging.git"

Import paths for concrete providers
-----------------------------------

Concrete providers are imported from their module so third-party SDK
dependencies stay optional::

    from messaging.providers.meta import MetaWhatsAppProvider
    from messaging.providers.whatsapp_personal import WhatsAppPersonalProvider
    from messaging.providers.twilio import TwilioProvider, empty_messaging_response_xml
    from messaging.content_api import TwilioContentAPI, TwilioContentAPIError, TwilioTemplateResponse
    from messaging.email.sendgrid import SendGridProvider
    from messaging.email.smtp2go import Smtp2GoProvider
    from messaging.sms.twilio import TwilioSMSProvider
    from messaging.telegram.bot_api import TelegramBotProvider

Quick start — WhatsApp via Meta Cloud API (base install)::

    from messaging import MetaWhatsAppConfig, WhatsAppText
    from messaging.providers.meta import MetaWhatsAppProvider

    provider = MetaWhatsAppProvider(MetaWhatsAppConfig(
        phone_number_id="123456789",
        access_token="EAAxxxxxxx...",
    ))
    result = provider.send(WhatsAppText(to="+5511999999999", body="Hello!"))
    if result.succeeded:
        print(f"Message ID: {result.external_id}")

Quick start — WhatsApp via Twilio (``[twilio]`` extra)::

    from messaging import TwilioConfig, WhatsAppText
    from messaging.providers.twilio import TwilioProvider

    provider = TwilioProvider(TwilioConfig(
        account_sid="AC...",
        auth_token="...",
        whatsapp_number="whatsapp:+14155238886",
    ))
    result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello!"))

Quick start — SMS via Twilio (``[twilio]`` extra)::

    from messaging import SMSMessage, TwilioSMSConfig
    from messaging.sms.twilio import TwilioSMSProvider

    provider = TwilioSMSProvider(TwilioSMSConfig(
        account_sid="AC...",
        auth_token="...",
        from_number="+14155238886",
    ))
    result = provider.send(SMSMessage(to="+5511999999999", body="Your code is 123456"))

Quick start — Email via SendGrid (``[sendgrid]`` extra)::

    from messaging import EmailMessage, SendGridConfig
    from messaging.email.sendgrid import SendGridProvider

    provider = SendGridProvider(SendGridConfig(api_key="SG..."))
    result = provider.send(EmailMessage(
        to="user@example.com",
        subject="Welcome",
        html_content="<h1>Hello!</h1>",
        from_email="noreply@example.com",
        from_name="My App",
    ))

Quick start — Telegram via Bot API (base install)::

    from messaging import TelegramConfig, TelegramText
    from messaging.telegram.bot_api import TelegramBotProvider

    provider = TelegramBotProvider(TelegramConfig(bot_token="123456789:ABCdef..."))
    result = provider.send(TelegramText(chat_id=12345, body="Hello from Maia!"))

Template management — Twilio Content API (``[twilio]`` extra)::

    from messaging import TwilioConfig
    from messaging.content_api import TwilioContentAPI

    api = TwilioContentAPI(TwilioConfig(
        account_sid="AC...",
        auth_token="...",
        whatsapp_number="whatsapp:+14155238886",
    ))
    template = api.create_template(
        friendly_name="order_update",
        language="en",
        types={"twilio_text": {"body": "Your order {{1}} is {{2}}."}},
    )

With phone fallback (Brazilian 9-digit → 8-digit retry)::

    from messaging import MessagingGateway

    gateway = MessagingGateway(provider)
    result = gateway.send(message, phone_fallback=True)
    if result.used_fallback_number:
        print(f"Delivered using fallback: {result.used_fallback_number}")

For testing::

    from messaging import MockProvider, WhatsAppText

    provider = MockProvider()
    result = provider.send(WhatsAppText(to="+5511...", body="test"))
    assert result.succeeded
    assert len(provider.sent) == 1

Module overview
---------------
- ``types``         — Core dataclasses: Message types, DeliveryResult, configs
- ``gateway``       — MessagingGateway with phone fallback
- ``providers/``    — MessagingProvider protocol, Meta/Twilio/WhatsApp Personal providers
- ``email/``        — EmailProvider protocol, SendGrid/SMTP2GO providers
- ``sms/``          — SMSProvider protocol, Twilio SMS provider
- ``telegram/``     — TelegramProvider protocol, Telegram Bot API provider
- ``content_api``   — TwilioContentAPI for template CRUD
- ``phone/``        — Phone normalization (Brazil 8→9 digit, E.164, whatsapp: format)
- ``pricing``       — WhatsApp template cost calculator

What this library does NOT own (stays in the consuming app):
- Database models and CommunicationLog creation
- Integration/credential resolution (which Twilio account to use)
- Quota enforcement and billing
- Session lifecycle and routing
- WhatsApp session lifecycle (QR code, connection status)
- Status webhook processing (DB updates, event bus)
"""

from __future__ import annotations

from .email.base import EmailProvider
from .gateway import MessagingGateway
from .mock import MockProvider, SentMessage
from .phone import (
    denormalize_phone_for_whatsapp,
    format_whatsapp_number,
    is_bsuid,
    normalize_phone,
    normalize_whatsapp_id,
    phones_match,
)
from .pricing import TEMPLATE_PRICING, calculate_template_cost
from .providers.base import MessagingProvider
from .providers.meta_schemas import (
    MetaCTAAction,
    MetaCTAMessage,
    MetaCTAParameters,
    MetaCTAPayload,
    MetaContact,
    MetaContactEmail,
    MetaContactName,
    MetaContactOrg,
    MetaContactPhone,
    MetaContactUrl,
    MetaContactsMessage,
    MetaErrorDetail,
    MetaErrorResponse,
    MetaInteractiveAction,
    MetaInteractiveBody,
    MetaInteractiveFooter,
    MetaInteractiveHeader,
    MetaInteractiveMessage,
    MetaInteractivePayload,
    MetaListAction,
    MetaListMessage,
    MetaListPayload,
    MetaListRow,
    MetaListSection,
    MetaLocationCoordinates,
    MetaLocationMessage,
    MetaMediaMessage,
    MetaMediaObject,
    MetaMessageContact,
    MetaMessageEntry,
    MetaMessageResponse,
    MetaProductAction,
    MetaProductItem,
    MetaProductListAction,
    MetaProductListMessage,
    MetaProductListPayload,
    MetaProductMessage,
    MetaProductPayload,
    MetaProductSection,
    MetaReactionMessage,
    MetaReactionPayload,
    MetaReplyButton,
    MetaStickerMessage,
    MetaStickerObject,
    MetaTemplateComponentPayload,
    MetaTemplateLanguage,
    MetaTemplateMessage,
    MetaTemplateParameter,
    MetaTemplatePayload,
    MetaTextBody,
    MetaTextMessage,
)
from .sms.base import SMSProvider
from .telegram.base import TelegramMessage, TelegramProvider
from .telegram.schemas import (
    TelegramErrorResponse,
    TelegramMediaPayload,
    TelegramResultMessage,
    TelegramSuccessResponse,
    TelegramTextPayload,
)
from .types import (
    DeliveryResult,
    DeliveryStatus,
    EmailMessage,
    GatewayResult,
    Message,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    SendGridConfig,
    SMSMessage,
    Smtp2GoConfig,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
    TwilioConfig,
    TwilioSMSConfig,
    WhatsAppContacts,
    WhatsAppInteractiveCTA,
    WhatsAppInteractiveList,
    WhatsAppInteractiveReply,
    WhatsAppLocation,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppProduct,
    WhatsAppProductList,
    WhatsAppReaction,
    WhatsAppSticker,
    WhatsAppTemplate,
    WhatsAppText,
)

__all__ = [
    # Gateway
    "MessagingGateway",
    # Provider protocols
    "MessagingProvider",
    "EmailProvider",
    "SMSProvider",
    "TelegramProvider",
    # Mock provider (no external deps)
    "MockProvider",
    "SentMessage",
    # Types — WhatsApp
    "DeliveryResult",
    "DeliveryStatus",
    "GatewayResult",
    "Message",
    "MetaWhatsAppConfig",
    "MetaWhatsAppTemplate",
    "TwilioConfig",
    "WhatsAppContacts",
    "WhatsAppInteractiveCTA",
    "WhatsAppInteractiveList",
    "WhatsAppInteractiveReply",
    "WhatsAppLocation",
    "WhatsAppMedia",
    "WhatsAppPersonalConfig",
    "WhatsAppProduct",
    "WhatsAppProductList",
    "WhatsAppReaction",
    "WhatsAppSticker",
    "WhatsAppTemplate",
    "WhatsAppText",
    # Types — Email
    "EmailMessage",
    "SendGridConfig",
    "Smtp2GoConfig",
    # Types — SMS
    "SMSMessage",
    "TwilioSMSConfig",
    # Types — Telegram
    "TelegramMessage",
    "TelegramText",
    "TelegramMedia",
    "TelegramConfig",
    # Telegram Bot API schemas
    "TelegramErrorResponse",
    "TelegramMediaPayload",
    "TelegramResultMessage",
    "TelegramSuccessResponse",
    "TelegramTextPayload",
    # Meta WhatsApp API schemas
    "MetaCTAAction",
    "MetaCTAMessage",
    "MetaCTAParameters",
    "MetaCTAPayload",
    "MetaErrorDetail",
    "MetaErrorResponse",
    "MetaInteractiveAction",
    "MetaInteractiveBody",
    "MetaInteractiveFooter",
    "MetaInteractiveHeader",
    "MetaInteractiveMessage",
    "MetaInteractivePayload",
    "MetaListAction",
    "MetaListMessage",
    "MetaListPayload",
    "MetaListRow",
    "MetaListSection",
    "MetaMediaMessage",
    "MetaMediaObject",
    "MetaMessageContact",
    "MetaMessageEntry",
    "MetaMessageResponse",
    "MetaProductAction",
    "MetaProductItem",
    "MetaProductListAction",
    "MetaProductListMessage",
    "MetaProductListPayload",
    "MetaProductMessage",
    "MetaProductPayload",
    "MetaProductSection",
    "MetaContactsMessage",
    "MetaContact",
    "MetaContactEmail",
    "MetaContactName",
    "MetaContactOrg",
    "MetaContactPhone",
    "MetaContactUrl",
    "MetaLocationCoordinates",
    "MetaLocationMessage",
    "MetaReactionMessage",
    "MetaReactionPayload",
    "MetaReplyButton",
    "MetaStickerMessage",
    "MetaStickerObject",
    "MetaTemplateComponentPayload",
    "MetaTemplateLanguage",
    "MetaTemplateMessage",
    "MetaTemplateParameter",
    "MetaTemplatePayload",
    "MetaTextBody",
    "MetaTextMessage",
    # Phone
    "denormalize_phone_for_whatsapp",
    "format_whatsapp_number",
    "is_bsuid",
    "normalize_phone",
    "normalize_whatsapp_id",
    "phones_match",
    # Pricing
    "TEMPLATE_PRICING",
    "calculate_template_cost",
]
