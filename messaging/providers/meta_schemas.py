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
    # Outbound: Interactive reply buttons
    "MetaReplyButton",
    "MetaInteractiveAction",
    "MetaInteractiveBody",
    "MetaInteractivePayload",
    "MetaInteractiveMessage",
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


# ── Outbound: Interactive reply buttons ─────────────────────────────


class MetaReplyButton(BaseModel):
    type: str = "reply"
    reply: dict[str, str]


class MetaInteractiveAction(BaseModel):
    buttons: list[MetaReplyButton]


class MetaInteractiveBody(BaseModel):
    text: str


class MetaInteractivePayload(BaseModel):
    type: str = "button"
    body: MetaInteractiveBody
    action: MetaInteractiveAction


class MetaInteractiveMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: MetaInteractivePayload


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
