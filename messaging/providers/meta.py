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
    MetaCTAAction,
    MetaCTAMessage,
    MetaCTAParameters,
    MetaCTAPayload,
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
    MetaMediaMessage,
    MetaMediaObject,
    MetaMessageResponse,
    MetaProductAction,
    MetaProductItem,
    MetaProductListAction,
    MetaProductListMessage,
    MetaProductListPayload,
    MetaProductMessage,
    MetaProductPayload,
    MetaProductSection,
    MetaContactsMessage,
    MetaContact,
    MetaContactEmail,
    MetaContactName,
    MetaContactOrg,
    MetaContactPhone,
    MetaContactUrl,
    MetaLocationCoordinates,
    MetaLocationMessage,
    MetaReactionMessage,
    MetaReactionPayload,
    MetaReplyButton,
    MetaStickerMessage,
    MetaStickerObject,
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
    WhatsAppContacts,
    WhatsAppInteractiveCTA,
    WhatsAppInteractiveList,
    WhatsAppInteractiveReply,
    WhatsAppLocation,
    WhatsAppMedia,
    WhatsAppProduct,
    WhatsAppProductList,
    WhatsAppReaction,
    WhatsAppSticker,
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
        if isinstance(message, WhatsAppInteractiveReply):
            return self._send_interactive(message)
        if isinstance(message, WhatsAppInteractiveList):
            return self._send_list(message)
        if isinstance(message, WhatsAppInteractiveCTA):
            return self._send_cta(message)
        if isinstance(message, WhatsAppProduct):
            return self._send_product(message)
        if isinstance(message, WhatsAppProductList):
            return self._send_product_list(message)
        if isinstance(message, WhatsAppLocation):
            return self._send_location(message)
        if isinstance(message, WhatsAppContacts):
            return self._send_contacts(message)
        if isinstance(message, WhatsAppReaction):
            return self._send_reaction(message)
        if isinstance(message, WhatsAppSticker):
            return self._send_sticker(message)
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

    def _send_interactive(self, message: WhatsAppInteractiveReply) -> DeliveryResult:
        if not message.body or not message.body.strip():
            return DeliveryResult.fail("No message body provided")
        if not message.buttons:
            return DeliveryResult.fail("No buttons provided")

        body = message.body.strip()
        if len(body) > 1024:
            body = body[:1024]

        buttons = [MetaReplyButton(reply={"id": btn["id"], "title": btn["title"][:20]}) for btn in message.buttons[:3]]
        msg = MetaInteractiveMessage(
            to=_normalize_recipient(message.to),
            interactive=MetaInteractivePayload(
                body=MetaInteractiveBody(text=body),
                action=MetaInteractiveAction(buttons=buttons),
            ),
        )
        return self._post(msg.model_dump())

    def _send_list(self, message: WhatsAppInteractiveList) -> DeliveryResult:
        if not message.body or not message.body.strip():
            return DeliveryResult.fail("No message body provided")
        if not message.button or not message.button.strip():
            return DeliveryResult.fail("No button text provided")
        if not message.sections:
            return DeliveryResult.fail("No sections provided")

        body = message.body.strip()[:1024]
        button_text = message.button.strip()[:20]

        rows_total = 0
        sections: list[MetaListSection] = []
        for section in message.sections:
            raw_rows = section.get("rows", [])
            rows = [
                MetaListRow(
                    id=row["id"],
                    title=row["title"][:24],
                    description=row.get("description", "")[:72] if row.get("description") else None,
                )
                for row in raw_rows
            ]
            rows_total += len(rows)
            sections.append(MetaListSection(title=section.get("title"), rows=rows))

        if rows_total == 0:
            return DeliveryResult.fail("No rows provided in sections")
        if rows_total > 10:
            return DeliveryResult.fail(f"Too many rows ({rows_total}); maximum is 10")

        header = MetaInteractiveHeader(text=message.header[:60]) if message.header else None
        footer = MetaInteractiveFooter(text=message.footer[:60]) if message.footer else None

        msg = MetaListMessage(
            to=_normalize_recipient(message.to),
            interactive=MetaListPayload(
                header=header,
                body=MetaInteractiveBody(text=body),
                footer=footer,
                action=MetaListAction(button=button_text, sections=sections),
            ),
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_cta(self, message: WhatsAppInteractiveCTA) -> DeliveryResult:
        if not message.body or not message.body.strip():
            return DeliveryResult.fail("No message body provided")
        if not message.url or not message.url.strip():
            return DeliveryResult.fail("No URL provided")
        if not message.display_text or not message.display_text.strip():
            return DeliveryResult.fail("No display text provided")

        body = message.body.strip()[:1024]
        display_text = message.display_text.strip()[:20]
        url = message.url.strip()[:2000]

        header = MetaInteractiveHeader(text=message.header[:60]) if message.header else None
        footer = MetaInteractiveFooter(text=message.footer[:60]) if message.footer else None

        msg = MetaCTAMessage(
            to=_normalize_recipient(message.to),
            interactive=MetaCTAPayload(
                header=header,
                body=MetaInteractiveBody(text=body),
                footer=footer,
                action=MetaCTAAction(parameters=MetaCTAParameters(display_text=display_text, url=url)),
            ),
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_product(self, message: WhatsAppProduct) -> DeliveryResult:
        if not message.body or not message.body.strip():
            return DeliveryResult.fail("No message body provided")
        if not message.catalog_id:
            return DeliveryResult.fail("No catalog_id provided")
        if not message.product_retailer_id:
            return DeliveryResult.fail("No product_retailer_id provided")

        body = message.body.strip()[:1024]
        footer = MetaInteractiveFooter(text=message.footer[:60]) if message.footer else None

        msg = MetaProductMessage(
            to=_normalize_recipient(message.to),
            interactive=MetaProductPayload(
                body=MetaInteractiveBody(text=body),
                footer=footer,
                action=MetaProductAction(
                    catalog_id=message.catalog_id,
                    product_retailer_id=message.product_retailer_id,
                ),
            ),
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_product_list(self, message: WhatsAppProductList) -> DeliveryResult:
        if not message.body or not message.body.strip():
            return DeliveryResult.fail("No message body provided")
        if not message.header or not message.header.strip():
            return DeliveryResult.fail("No header provided")
        if not message.catalog_id:
            return DeliveryResult.fail("No catalog_id provided")
        if not message.sections:
            return DeliveryResult.fail("No sections provided")

        body = message.body.strip()[:1024]
        header_text = message.header.strip()[:60]
        footer = MetaInteractiveFooter(text=message.footer[:60]) if message.footer else None

        product_total = 0
        sections: list[MetaProductSection] = []
        for section in message.sections:
            items = [
                MetaProductItem(product_retailer_id=p["product_retailer_id"]) for p in section.get("product_items", [])
            ]
            product_total += len(items)
            sections.append(MetaProductSection(title=section["title"], product_items=items))

        if product_total == 0:
            return DeliveryResult.fail("No products provided in sections")
        if product_total > 30:
            return DeliveryResult.fail(f"Too many products ({product_total}); maximum is 30")
        if len(sections) > 10:
            return DeliveryResult.fail(f"Too many sections ({len(sections)}); maximum is 10")

        msg = MetaProductListMessage(
            to=_normalize_recipient(message.to),
            interactive=MetaProductListPayload(
                header=MetaInteractiveHeader(text=header_text),
                body=MetaInteractiveBody(text=body),
                footer=footer,
                action=MetaProductListAction(catalog_id=message.catalog_id, sections=sections),
            ),
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_location(self, message: WhatsAppLocation) -> DeliveryResult:
        msg = MetaLocationMessage(
            to=_normalize_recipient(message.to),
            location=MetaLocationCoordinates(
                latitude=message.latitude,
                longitude=message.longitude,
                name=message.name,
                address=message.address,
            ),
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_contacts(self, message: WhatsAppContacts) -> DeliveryResult:
        if not message.contacts:
            return DeliveryResult.fail("No contacts provided")

        meta_contacts: list[MetaContact] = []
        for contact in message.contacts:
            name_data = contact.get("name", {})
            name = MetaContactName(
                formatted_name=name_data.get("formatted_name", ""),
                first_name=name_data.get("first_name"),
                last_name=name_data.get("last_name"),
            )
            phones = (
                [MetaContactPhone(phone=p["phone"], type=p.get("type")) for p in contact["phones"]]
                if contact.get("phones")
                else None
            )
            emails = (
                [MetaContactEmail(email=e["email"], type=e.get("type")) for e in contact["emails"]]
                if contact.get("emails")
                else None
            )
            org = MetaContactOrg(**contact["org"]) if contact.get("org") else None
            urls = (
                [MetaContactUrl(url=u["url"], type=u.get("type")) for u in contact["urls"]]
                if contact.get("urls")
                else None
            )
            meta_contacts.append(MetaContact(name=name, phones=phones, emails=emails, org=org, urls=urls))

        msg = MetaContactsMessage(
            to=_normalize_recipient(message.to),
            contacts=meta_contacts,
        )
        return self._post(msg.model_dump(exclude_none=True))

    def _send_reaction(self, message: WhatsAppReaction) -> DeliveryResult:
        if not message.message_id:
            return DeliveryResult.fail("No message_id provided")

        msg = MetaReactionMessage(
            to=_normalize_recipient(message.to),
            reaction=MetaReactionPayload(
                message_id=message.message_id,
                emoji=message.emoji,
            ),
        )
        return self._post(msg.model_dump())

    def _send_sticker(self, message: WhatsAppSticker) -> DeliveryResult:
        if not message.sticker:
            return DeliveryResult.fail("No sticker provided")

        # Determine if it's a URL or a media ID
        sticker_value = message.sticker.strip()
        if sticker_value.startswith(("http://", "https://")):
            sticker_obj = MetaStickerObject(link=sticker_value)
        else:
            sticker_obj = MetaStickerObject(id=sticker_value)

        msg = MetaStickerMessage(
            to=_normalize_recipient(message.to),
            sticker=sticker_obj,
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
