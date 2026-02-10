"""
maia-messaging — Multi-channel messaging delivery library.

Standalone messaging gateway extracted from the Meu Assistente IA backend.
Owns everything from "I have a resolved message and provider config" to
"here's what happened." The consuming app retains orchestration (who to send
to, which provider account, quota, logging).

Installation::

    pip install maia-messaging@git+https://github.com/carboni123/maia-messaging.git

Quick start — WhatsApp via Twilio::

    from messaging import TwilioProvider, TwilioConfig, WhatsAppText

    provider = TwilioProvider(TwilioConfig(
        account_sid="AC...",
        auth_token="...",
        whatsapp_number="whatsapp:+14155238886",
    ))
    result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello!"))
    if result.succeeded:
        print(f"Message SID: {result.external_id}")

Quick start — SMS via Twilio::

    from messaging import TwilioSMSProvider, TwilioSMSConfig, SMSMessage

    provider = TwilioSMSProvider(TwilioSMSConfig(
        account_sid="AC...",
        auth_token="...",
        from_number="+14155238886",
    ))
    result = provider.send(SMSMessage(to="+5511999999999", body="Your code is 123456"))
    if result.succeeded:
        print(f"SMS SID: {result.external_id}")

Quick start — Email via SendGrid::

    from messaging import SendGridProvider, SendGridConfig, EmailMessage

    provider = SendGridProvider(SendGridConfig(api_key="SG..."))
    result = provider.send(EmailMessage(
        to="user@example.com",
        subject="Welcome",
        html_content="<h1>Hello!</h1>",
        from_email="noreply@example.com",
        from_name="My App",
    ))
    if result.succeeded:
        print("Email sent!")

Quick start — Telegram via Bot API::

    from messaging import TelegramBotProvider, TelegramConfig, TelegramText

    provider = TelegramBotProvider(TelegramConfig(bot_token="123456789:ABCdef..."))
    result = provider.send(TelegramText(chat_id=12345, body="Hello from Maia!"))
    if result.succeeded:
        print(f"Message ID: {result.external_id}")

Template management — Twilio Content API::

    from messaging import TwilioContentAPI, TwilioConfig

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

    from messaging import MockProvider

    provider = MockProvider()
    result = provider.send(WhatsAppText(to="+5511...", body="test"))
    assert result.succeeded
    assert len(provider.sent) == 1

Module overview
---------------
- ``types``         — Core dataclasses: Message types, DeliveryResult, configs
- ``gateway``       — MessagingGateway with phone fallback
- ``providers/``    — TwilioProvider, WhatsAppPersonalProvider, MockProvider
- ``email/``        — SendGridProvider, Smtp2GoProvider
- ``sms/``          — TwilioSMSProvider
- ``telegram/``     — TelegramBotProvider (Telegram Bot API)
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

from .content_api import TwilioContentAPI, TwilioContentAPIError, TwilioTemplateResponse
from .email import EmailProvider, SendGridProvider, Smtp2GoProvider
from .gateway import MessagingGateway
from .mock import MockProvider
from .phone import denormalize_phone_for_whatsapp, format_whatsapp_number, normalize_phone, normalize_whatsapp_id, phones_match
from .pricing import TEMPLATE_PRICING, calculate_template_cost
from .providers.base import MessagingProvider
from .providers.twilio import TwilioProvider, empty_messaging_response_xml
from .providers.whatsapp_personal import WhatsAppPersonalProvider
from .sms import SMSProvider, TwilioSMSProvider
from .telegram import TelegramBotProvider, TelegramProvider
from .types import (
    DeliveryResult,
    DeliveryStatus,
    EmailMessage,
    GatewayResult,
    Message,
    SMSMessage,
    SendGridConfig,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
    Smtp2GoConfig,
    TwilioConfig,
    TwilioSMSConfig,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppTemplate,
    WhatsAppText,
)

__all__ = [
    # Gateway
    "MessagingGateway",
    # WhatsApp Providers
    "MessagingProvider",
    "TwilioProvider",
    "WhatsAppPersonalProvider",
    "MockProvider",
    "empty_messaging_response_xml",
    # Email Providers
    "EmailProvider",
    "SendGridProvider",
    "Smtp2GoProvider",
    # Template Management
    "TwilioContentAPI",
    "TwilioContentAPIError",
    "TwilioTemplateResponse",
    # Types — WhatsApp
    "DeliveryResult",
    "DeliveryStatus",
    "GatewayResult",
    "Message",
    "TwilioConfig",
    "WhatsAppMedia",
    "WhatsAppPersonalConfig",
    "WhatsAppTemplate",
    "WhatsAppText",
    # Types — Email
    "EmailMessage",
    "SendGridConfig",
    "Smtp2GoConfig",
    # SMS Providers
    "SMSProvider",
    "TwilioSMSProvider",
    # Types — SMS
    "SMSMessage",
    "TwilioSMSConfig",
    # Telegram Providers
    "TelegramProvider",
    "TelegramBotProvider",
    # Types — Telegram
    "TelegramText",
    "TelegramMedia",
    "TelegramConfig",
    # Phone
    "denormalize_phone_for_whatsapp",
    "format_whatsapp_number",
    "normalize_phone",
    "normalize_whatsapp_id",
    "phones_match",
    # Pricing
    "TEMPLATE_PRICING",
    "calculate_template_cost",
]
