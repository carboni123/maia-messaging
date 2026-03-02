"""Twilio WhatsApp messaging provider."""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any

from twilio.base.exceptions import TwilioRestException  # type: ignore[import-untyped]
from twilio.http.http_client import TwilioHttpClient  # type: ignore[import-untyped]
from twilio.rest import Client  # type: ignore[import-untyped]
from twilio.twiml.messaging_response import MessagingResponse  # type: ignore[import-untyped]

from messaging.twilio_utils import map_twilio_status
from messaging.types import (
    DeliveryResult,
    Message,
    MetaWhatsAppTemplate,
    TwilioConfig,
    WhatsAppMedia,
    WhatsAppTemplate,
    WhatsAppText,
)

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 1532
DEFAULT_TIMEOUT_SECONDS = 10.0


@lru_cache(maxsize=1)
def empty_messaging_response_xml() -> str:
    """Return the canonical empty Twilio MessagingResponse payload as XML.

    Used by webhook handlers to acknowledge receipt without sending a reply.
    """
    return str(MessagingResponse())


class TwilioProvider:
    """Sends WhatsApp messages via Twilio REST API.

    Supports text, media, and template messages. Provides both sync
    and async send methods.
    """

    def __init__(self, config: TwilioConfig) -> None:
        if not config.whatsapp_number:
            raise ValueError("TwilioConfig.whatsapp_number is required for message delivery")
        self._config = config
        http_client = TwilioHttpClient(timeout=DEFAULT_TIMEOUT_SECONDS)
        self._client = Client(config.account_sid, config.auth_token, http_client=http_client)

    def close(self) -> None:
        """No-op for SDK-based provider (Twilio SDK manages its own connections)."""

    def __enter__(self) -> TwilioProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    async def __aenter__(self) -> TwilioProvider:
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.close()

    # ── Public API ────────────────────────────────────────────────

    def send(self, message: Message) -> DeliveryResult:
        """Send a message synchronously."""
        if isinstance(message, WhatsAppText):
            return self._send_text(message)
        if isinstance(message, WhatsAppMedia):
            return self._send_media(message)
        if isinstance(message, WhatsAppTemplate):
            return self._send_template(message)
        if isinstance(message, MetaWhatsAppTemplate):
            return DeliveryResult.fail(
                "TwilioProvider does not support MetaWhatsAppTemplate; use MetaWhatsAppProvider"
            )
        return DeliveryResult.fail(f"Unsupported message type: {type(message).__name__}")

    async def send_async(self, message: Message) -> DeliveryResult:
        """Send a message asynchronously (runs sync send in a thread)."""
        return await asyncio.to_thread(self.send, message)

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Poll Twilio for current message status."""
        try:
            msg = self._client.messages(external_id).fetch()
            status = map_twilio_status(getattr(msg, "status", None))
            return DeliveryResult(
                status=status,
                external_id=msg.sid,
                error_code=str(msg.error_code) if msg.error_code else None,
                error_message=msg.error_message,
            )
        except TwilioRestException as exc:
            logger.error("Failed to fetch message status for %s: %s", external_id, exc)
            return DeliveryResult.fail(str(exc.msg), error_code=str(exc.code) if exc.code else None)
        except Exception as exc:
            logger.error("Failed to fetch message status for %s: %s", external_id, exc)
            return None

    # ── Private dispatch ──────────────────────────────────────────

    def _send_text(self, message: WhatsAppText) -> DeliveryResult:
        body = message.body.strip()
        if not body:
            return DeliveryResult.fail("No message body provided")

        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS]

        params: dict[str, Any] = {
            "to": message.to,
            "from_": self._config.whatsapp_number,
            "body": body,
        }
        if self._config.status_callback:
            params["status_callback"] = self._config.status_callback

        return self._create_message(params)

    def _send_media(self, message: WhatsAppMedia) -> DeliveryResult:
        if not message.media_urls:
            return DeliveryResult.fail("No media URLs provided")

        params: dict[str, Any] = {
            "to": message.to,
            "from_": self._config.whatsapp_number,
            "media_url": message.media_urls,
        }

        caption = message.caption
        if caption:
            if len(caption) > MAX_BODY_CHARS:
                caption = caption[:MAX_BODY_CHARS]
            params["body"] = caption

        if self._config.status_callback:
            params["status_callback"] = self._config.status_callback

        return self._create_message(params)

    def _send_template(self, message: WhatsAppTemplate) -> DeliveryResult:
        params: dict[str, Any] = {
            "to": message.to,
            "from_": self._config.whatsapp_number,
            "content_sid": message.content_sid,
            "content_variables": json.dumps(message.content_variables),
        }
        if self._config.status_callback:
            params["status_callback"] = self._config.status_callback

        return self._create_message(params)

    def _create_message(self, params: dict[str, Any]) -> DeliveryResult:
        try:
            msg = self._client.messages.create(**params)
            status = map_twilio_status(getattr(msg, "status", None))
            return DeliveryResult(
                status=status,
                external_id=getattr(msg, "sid", None),
                error_code=str(msg.error_code) if getattr(msg, "error_code", None) else None,
                error_message=getattr(msg, "error_message", None),
            )
        except TwilioRestException as exc:
            logger.error("Twilio API error: code=%s msg=%s", exc.code, exc.msg)
            return DeliveryResult.fail(str(exc.msg), error_code=str(exc.code) if exc.code else None)
        except Exception as exc:
            logger.error("Twilio send failed: %s", exc)
            return DeliveryResult.fail(str(exc))
