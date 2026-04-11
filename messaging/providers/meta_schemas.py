"""Pydantic models for Meta WhatsApp Cloud API request/response payloads."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    # Outbound: Text
    "MetaTextBody",
    "MetaTextMessage",
    # Outbound: Media
    "MetaMediaObject",
    "MetaMediaMessage",
    # Outbound: Template
    "MetaTemplateParameter",
    "MetaTemplateComponentPayload",
    "MetaTemplateLanguage",
    "MetaTemplatePayload",
    "MetaTemplateMessage",
    # Outbound: Interactive — shared
    "MetaInteractiveBody",
    "MetaInteractiveHeader",
    "MetaInteractiveFooter",
    # Outbound: Interactive — reply buttons
    "MetaReplyButton",
    "MetaInteractiveAction",
    "MetaInteractivePayload",
    "MetaInteractiveMessage",
    # Outbound: Interactive — list
    "MetaListRow",
    "MetaListSection",
    "MetaListAction",
    "MetaListPayload",
    "MetaListMessage",
    # Outbound: Interactive — CTA URL
    "MetaCTAParameters",
    "MetaCTAAction",
    "MetaCTAPayload",
    "MetaCTAMessage",
    # Outbound: Interactive — product
    "MetaProductAction",
    "MetaProductPayload",
    "MetaProductMessage",
    # Outbound: Interactive — product list
    "MetaProductItem",
    "MetaProductSection",
    "MetaProductListAction",
    "MetaProductListPayload",
    "MetaProductListMessage",
    # Inbound: Success response
    "MetaMessageContact",
    "MetaMessageEntry",
    "MetaMessageResponse",
    # Inbound: Error response
    "MetaErrorDetail",
    "MetaErrorResponse",
]


# ── Outbound: Text ───────────────────────────────────────────────────


class MetaTextBody(BaseModel):
    body: str


class MetaTextMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "text"
    text: MetaTextBody


# ── Outbound: Media ──────────────────────────────────────────────────


class MetaMediaObject(BaseModel):
    link: str
    caption: str | None = None


class MetaMediaMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str  # "image", "video", "audio", "document"
    image: MetaMediaObject | None = None
    video: MetaMediaObject | None = None
    audio: MetaMediaObject | None = None
    document: MetaMediaObject | None = None


# ── Outbound: Template ───────────────────────────────────────────────


class MetaTemplateParameter(BaseModel):
    type: str = "text"
    text: str


class MetaTemplateComponentPayload(BaseModel):
    type: str = "body"
    parameters: list[MetaTemplateParameter]


class MetaTemplateLanguage(BaseModel):
    code: str


class MetaTemplatePayload(BaseModel):
    name: str
    language: MetaTemplateLanguage
    components: list[MetaTemplateComponentPayload] | None = None


class MetaTemplateMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "template"
    template: MetaTemplatePayload


# ── Outbound: Interactive — shared building blocks ─────────────────


class MetaInteractiveBody(BaseModel):
    text: str


class MetaInteractiveHeader(BaseModel):
    type: str = "text"
    text: str


class MetaInteractiveFooter(BaseModel):
    text: str


# ── Outbound: Interactive — reply buttons ──────────────────────────


class MetaReplyButton(BaseModel):
    type: str = "reply"
    reply: dict[str, str]


class MetaInteractiveAction(BaseModel):
    buttons: list[MetaReplyButton]


class MetaInteractivePayload(BaseModel):
    type: str = "button"
    body: MetaInteractiveBody
    action: MetaInteractiveAction


class MetaInteractiveMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaInteractivePayload


# ── Outbound: Interactive — list ───────────────────────────────────


class MetaListRow(BaseModel):
    id: str
    title: str
    description: str | None = None


class MetaListSection(BaseModel):
    title: str | None = None
    rows: list[MetaListRow]


class MetaListAction(BaseModel):
    button: str
    sections: list[MetaListSection]


class MetaListPayload(BaseModel):
    type: str = "list"
    header: MetaInteractiveHeader | None = None
    body: MetaInteractiveBody
    footer: MetaInteractiveFooter | None = None
    action: MetaListAction


class MetaListMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaListPayload


# ── Outbound: Interactive — CTA URL ────────────────────────────────


class MetaCTAParameters(BaseModel):
    display_text: str
    url: str


class MetaCTAAction(BaseModel):
    name: str = "cta_url"
    parameters: MetaCTAParameters


class MetaCTAPayload(BaseModel):
    type: str = "cta_url"
    header: MetaInteractiveHeader | None = None
    body: MetaInteractiveBody
    footer: MetaInteractiveFooter | None = None
    action: MetaCTAAction


class MetaCTAMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaCTAPayload


# ── Outbound: Interactive — product ────────────────────────────────


class MetaProductAction(BaseModel):
    catalog_id: str
    product_retailer_id: str


class MetaProductPayload(BaseModel):
    type: str = "product"
    body: MetaInteractiveBody
    footer: MetaInteractiveFooter | None = None
    action: MetaProductAction


class MetaProductMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaProductPayload


# ── Outbound: Interactive — product list ───────────────────────────


class MetaProductItem(BaseModel):
    product_retailer_id: str


class MetaProductSection(BaseModel):
    title: str
    product_items: list[MetaProductItem]


class MetaProductListAction(BaseModel):
    catalog_id: str
    sections: list[MetaProductSection]


class MetaProductListPayload(BaseModel):
    type: str = "product_list"
    header: MetaInteractiveHeader
    body: MetaInteractiveBody
    footer: MetaInteractiveFooter | None = None
    action: MetaProductListAction


class MetaProductListMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaProductListPayload


# ── Inbound: Success response ────────────────────────────────────────


class MetaMessageContact(BaseModel):
    input: str
    wa_id: str


class MetaMessageEntry(BaseModel):
    id: str
    message_status: str | None = None


class MetaMessageResponse(BaseModel):
    messaging_product: str
    contacts: list[MetaMessageContact]
    messages: list[MetaMessageEntry]


# ── Inbound: Error response ──────────────────────────────────────────


class MetaErrorDetail(BaseModel):
    message: str
    type: str | None = None
    code: int | None = None
    fbtrace_id: str | None = None


class MetaErrorResponse(BaseModel):
    error: MetaErrorDetail
