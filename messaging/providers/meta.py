"""Meta WhatsApp Cloud API provider."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from messaging.types import (
    DeliveryResult,
    DeliveryStatus,
    Message,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    WhatsAppMedia,
    WhatsAppTemplate,
    WhatsAppText,
)

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com"

MAX_BODY_CHARS = 4096

# Maps MIME type prefixes to Meta Cloud API media types.
_MIME_TO_META_TYPE: dict[str, str] = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
}


def _normalize_phone(to: str) -> str:
    """Strip 'whatsapp:' prefix and '+' to get a plain phone number for Meta API."""
    phone = re.sub(r"^whatsapp:", "", to, flags=re.IGNORECASE)
    return phone.lstrip("+")


def _media_type_from_mime(mime: str) -> str:
    """Determine Meta media type from a MIME type string. Defaults to 'document'."""
    mime_lower = mime.lower()
    for prefix, meta_type in _MIME_TO_META_TYPE.items():
        if mime_lower.startswith(prefix):
            return meta_type
    return "document"


class MetaWhatsAppProvider:
    """Sends WhatsApp messages via the Meta Cloud API.

    Supports text, media, and template messages. Uses the same
    ``MessagingProvider`` protocol as ``TwilioProvider``, sharing
    ``WhatsAppText`` and ``WhatsAppMedia`` message types.

    Templates use ``MetaWhatsAppTemplate`` (not ``WhatsAppTemplate``)
    because Meta's template format differs from Twilio's Content API.

    Status tracking is via webhooks only — ``fetch_status()`` returns None.
    """

    def __init__(self, config: MetaWhatsAppConfig) -> None:
        if not config.phone_number_id:
            raise ValueError("phone_number_id is required")
        if not config.access_token:
            raise ValueError("access_token is required")
        self._config = config
        self._url = f"{META_API_BASE}/{config.api_version}/{config.phone_number_id}/messages"

    # ── Public API ────────────────────────────────────────────────

    def send(self, message: Message) -> DeliveryResult:
        """Send a message via Meta WhatsApp Cloud API."""
        if isinstance(message, WhatsAppText):
            return self._send_text(message)
        if isinstance(message, WhatsAppMedia):
            return self._send_media(message)
        if isinstance(message, MetaWhatsAppTemplate):
            return self._send_template(message)
        if isinstance(message, WhatsAppTemplate):
            return DeliveryResult.fail(
                "MetaWhatsAppProvider does not support WhatsAppTemplate; use MetaWhatsAppTemplate"
            )
        return DeliveryResult.fail(f"Unsupported message type: {type(message).__name__}")

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Meta Cloud API does not support status polling (webhooks only)."""
        return None

    # ── Private dispatch ──────────────────────────────────────────

    def _send_text(self, message: WhatsAppText) -> DeliveryResult:
        body = message.body.strip()
        if not body:
            return DeliveryResult.fail("No message body provided")
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS]

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": _normalize_phone(message.to),
            "type": "text",
            "text": {"body": body},
        }
        return self._post(payload)

    def _send_media(self, message: WhatsAppMedia) -> DeliveryResult:
        if not message.media_urls:
            return DeliveryResult.fail("No media URLs provided")

        to = _normalize_phone(message.to)
        last_result: DeliveryResult | None = None

        for idx, media_url in enumerate(message.media_urls):
            mime = message.media_types[idx] if idx < len(message.media_types) else ""
            meta_type = _media_type_from_mime(mime)

            media_obj: dict[str, Any] = {"link": media_url}
            # Meta Cloud API only supports captions on image, video, and document — not audio.
            if message.caption and idx == 0 and meta_type != "audio":
                media_obj["caption"] = message.caption

            payload: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": meta_type,
                meta_type: media_obj,
            }
            last_result = self._post(payload)
            if not last_result.succeeded:
                return last_result

        assert last_result is not None  # guaranteed by non-empty media_urls
        return last_result

    def _send_template(self, message: MetaWhatsAppTemplate) -> DeliveryResult:
        template_obj: dict[str, Any] = {
            "name": message.template_name,
            "language": {"code": message.language_code},
        }
        if message.components:
            template_obj["components"] = message.components

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": _normalize_phone(message.to),
            "type": "template",
            "template": template_obj,
        }
        return self._post(payload)

    def _post(self, payload: dict[str, Any]) -> DeliveryResult:
        """Make a POST request to the Meta WhatsApp Cloud API."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self._url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._config.access_token}",
                        "Content-Type": "application/json",
                    },
                )

            data = response.json()

            # Meta error response format: {"error": {"message": ..., "code": ...}}
            if "error" in data:
                error = data["error"]
                error_code = str(error.get("code", ""))
                description = error.get("message", "Unknown Meta API error")
                logger.error("Meta WhatsApp API error: [%s] %s", error_code, description)
                return DeliveryResult.fail(description, error_code=error_code)

            # Success response: {"messages": [{"id": "wamid.xxx"}]}
            messages = data.get("messages", [])
            external_id = messages[0]["id"] if messages else None
            logger.info("WhatsApp message sent via Meta Cloud API, wamid=%s", external_id)
            return DeliveryResult.ok(status=DeliveryStatus.SENT, external_id=external_id)

        except Exception as exc:
            logger.exception("Unexpected error calling Meta WhatsApp Cloud API")
            return DeliveryResult.fail(str(exc))
