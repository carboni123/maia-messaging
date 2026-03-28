"""Meta WhatsApp Cloud API provider."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from typing import Any

import httpx
from pydantic import ValidationError

from messaging.providers.meta_schemas import (
    MetaErrorResponse,
    MetaMediaMessage,
    MetaMediaObject,
    MetaMessageResponse,
    MetaTemplateComponentPayload,
    MetaTemplateLanguage,
    MetaTemplateMessage,
    MetaTemplatePayload,
    MetaTextBody,
    MetaTextMessage,
)
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
DEFAULT_TIMEOUT_SECONDS = 10.0

# Maps MIME type prefixes to Meta Cloud API media types.
_MIME_TO_META_TYPE: dict[str, str] = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
}


_BSUID_PATTERN = re.compile(r"^[A-Za-z]{2}\.[A-Za-z0-9]+$")


def _normalize_recipient(to: str) -> str:
    """Normalize a recipient identifier for the Meta API.

    For phone numbers: strips ``whatsapp:`` prefix and leading ``+``.
    For BSUIDs: strips ``whatsapp:`` prefix only (preserves the ``CC.xxx`` format).
    """
    stripped = re.sub(r"^whatsapp:", "", to, flags=re.IGNORECASE)
    if _BSUID_PATTERN.match(stripped):
        return stripped
    return stripped.lstrip("+")


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
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
        self._lock = threading.Lock()
        self._headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> MetaWhatsAppProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    async def __aenter__(self) -> MetaWhatsAppProvider:
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.close()

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

    async def send_async(self, message: Message) -> DeliveryResult:
        """Send a message asynchronously (thread-safe via lock)."""

        def _send() -> DeliveryResult:
            with self._lock:
                return self.send(message)

        return await asyncio.to_thread(_send)

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

        msg = MetaTextMessage(
            to=_normalize_recipient(message.to),
            text=MetaTextBody(body=body),
        )
        return self._post(msg.model_dump())

    def _send_media(self, message: WhatsAppMedia) -> DeliveryResult:
        if not message.media_urls:
            return DeliveryResult.fail("No media URLs provided")

        to = _normalize_recipient(message.to)
        last_result: DeliveryResult | None = None

        for idx, media_url in enumerate(message.media_urls):
            mime = message.media_types[idx] if idx < len(message.media_types) else ""
            meta_type = _media_type_from_mime(mime)

            caption = message.caption if (message.caption and idx == 0 and meta_type != "audio") else None
            media_obj = MetaMediaObject(link=media_url, caption=caption)

            msg = MetaMediaMessage.model_validate(
                {
                    "to": to,
                    "type": meta_type,
                    meta_type: media_obj,
                }
            )
            last_result = self._post(msg.model_dump(exclude_none=True))
            if not last_result.succeeded:
                return last_result

        if last_result is None:  # pragma: no cover — unreachable after non-empty check
            return DeliveryResult.fail("No media URLs processed")
        return last_result

    def _send_template(self, message: MetaWhatsAppTemplate) -> DeliveryResult:
        components = None
        if message.components:
            components = [MetaTemplateComponentPayload(**comp) for comp in message.components]
        template_payload = MetaTemplatePayload(
            name=message.template_name,
            language=MetaTemplateLanguage(code=message.language_code),
            components=components,
        )
        msg = MetaTemplateMessage(
            to=_normalize_recipient(message.to),
            template=template_payload,
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _post(self, payload: dict[str, Any]) -> DeliveryResult:
        """Make a POST request to the Meta WhatsApp Cloud API."""
        try:
            response = self._client.post(
                self._url,
                json=payload,
                headers=self._headers,
            )
            data = response.json()

            if "error" in data:
                error_resp = MetaErrorResponse.model_validate(data)
                error_code = str(error_resp.error.code) if error_resp.error.code is not None else ""
                description = error_resp.error.message
                logger.error("Meta WhatsApp API error: [%s] %s", error_code, description)
                return DeliveryResult.fail(description, error_code=error_code)

            success_resp = MetaMessageResponse.model_validate(data)
            external_id = success_resp.messages[0].id if success_resp.messages else None
            logger.info("WhatsApp message sent via Meta Cloud API, wamid=%s", external_id)
            return DeliveryResult.ok(status=DeliveryStatus.SENT, external_id=external_id)

        except ValidationError as exc:
            logger.exception("Failed to validate Meta API response")
            return DeliveryResult.fail(f"Invalid Meta API response: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error calling Meta WhatsApp Cloud API")
            return DeliveryResult.fail(str(exc))
