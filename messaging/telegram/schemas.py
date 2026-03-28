"""Pydantic models for Telegram Bot API request/response payloads."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    # Outbound: Text
    "TelegramTextPayload",
    # Outbound: Media
    "TelegramMediaPayload",
    # Inbound: Success response
    "TelegramResultMessage",
    "TelegramSuccessResponse",
    # Inbound: Error response
    "TelegramErrorResponse",
]


# ── Outbound: Text ───────────────────────────────────────────────────


class TelegramTextPayload(BaseModel):
    chat_id: str | int
    text: str
    parse_mode: str | None = None


# ── Outbound: Media ──────────────────────────────────────────────────


class TelegramMediaPayload(BaseModel):
    chat_id: str | int
    photo: str | None = None
    document: str | None = None
    video: str | None = None
    caption: str | None = None
    parse_mode: str | None = None


# ── Inbound: Success response ────────────────────────────────────────


class TelegramResultMessage(BaseModel):
    message_id: int


class TelegramSuccessResponse(BaseModel):
    ok: bool
    result: TelegramResultMessage


# ── Inbound: Error response ──────────────────────────────────────────


class TelegramErrorResponse(BaseModel):
    ok: bool
    error_code: int
    description: str
