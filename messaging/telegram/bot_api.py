"""Telegram Bot API provider."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from messaging.types import (
    DeliveryResult,
    DeliveryStatus,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
)

from .base import TelegramMessage

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"

_MEDIA_TYPE_ENDPOINTS: dict[str, str] = {
    "photo": "sendPhoto",
    "document": "sendDocument",
    "video": "sendVideo",
}


class TelegramBotProvider:
    """Sends messages via the Telegram Bot API."""

    def __init__(self, config: TelegramConfig) -> None:
        if not config.bot_token:
            raise ValueError("bot_token is required")
        self._base_url = f"{TELEGRAM_API_BASE}/bot{config.bot_token}"

    def send(self, message: TelegramMessage) -> DeliveryResult:
        """Send a message via Telegram Bot API."""
        if isinstance(message, TelegramText):
            return self._send_text(message)
        if isinstance(message, TelegramMedia):
            return self._send_media(message)
        return DeliveryResult.fail(f"Unsupported message type: {type(message).__name__}")

    def _send_text(self, message: TelegramText) -> DeliveryResult:
        """Send a text message via sendMessage."""
        payload: dict[str, Any] = {
            "chat_id": message.chat_id,
            "text": message.body,
        }
        if message.parse_mode:
            payload["parse_mode"] = message.parse_mode
        return self._post("sendMessage", payload)

    def _send_media(self, message: TelegramMedia) -> DeliveryResult:
        """Send a media message via sendPhoto/sendDocument/sendVideo."""
        endpoint = _MEDIA_TYPE_ENDPOINTS.get(message.media_type)
        if not endpoint:
            return DeliveryResult.fail(
                f"Unsupported media type: {message.media_type}",
                error_code="unsupported_media_type",
            )

        media_field = message.media_type  # "photo", "document", "video"
        payload: dict[str, Any] = {
            "chat_id": message.chat_id,
            media_field: message.media_url,
        }
        if message.caption:
            payload["caption"] = message.caption
        if message.parse_mode:
            payload["parse_mode"] = message.parse_mode
        return self._post(endpoint, payload)

    def _post(self, method: str, payload: dict[str, Any]) -> DeliveryResult:
        """Make a POST request to the Telegram Bot API."""
        url = f"{self._base_url}/{method}"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)

            data = response.json()

            if data.get("ok"):
                message_id = data.get("result", {}).get("message_id")
                external_id = str(message_id) if message_id is not None else None
                logger.info("Telegram message sent via %s, message_id=%s", method, external_id)
                return DeliveryResult.ok(status=DeliveryStatus.SENT, external_id=external_id)

            error_code = str(data.get("error_code", ""))
            description = data.get("description", "Unknown Telegram API error")
            logger.error("Telegram API error: [%s] %s", error_code, description)
            return DeliveryResult.fail(description, error_code=error_code)

        except Exception as exc:
            logger.exception("Unexpected error calling Telegram Bot API")
            return DeliveryResult.fail(str(exc))
