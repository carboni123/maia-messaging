"""Telegram Bot API provider."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

import httpx
from pydantic import ValidationError

from messaging.types import (
    DeliveryResult,
    DeliveryStatus,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
)

from .base import TelegramMessage
from .schemas import (
    TelegramErrorResponse,
    TelegramMediaPayload,
    TelegramSuccessResponse,
    TelegramTextPayload,
)

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT_SECONDS = 10.0

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
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
        self._lock = threading.Lock()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> TelegramBotProvider:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    async def __aenter__(self) -> TelegramBotProvider:
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.close()

    def send(self, message: TelegramMessage) -> DeliveryResult:
        """Send a message via Telegram Bot API."""
        if isinstance(message, TelegramText):
            return self._send_text(message)
        if isinstance(message, TelegramMedia):
            return self._send_media(message)
        return DeliveryResult.fail(f"Unsupported message type: {type(message).__name__}")

    async def send_async(self, message: TelegramMessage) -> DeliveryResult:
        """Send a message asynchronously (thread-safe via lock)."""

        def _send() -> DeliveryResult:
            with self._lock:
                return self.send(message)

        return await asyncio.to_thread(_send)

    def _send_text(self, message: TelegramText) -> DeliveryResult:
        """Send a text message via sendMessage."""
        msg = TelegramTextPayload(
            chat_id=message.chat_id,
            text=message.body,
            parse_mode=message.parse_mode,
        )
        return self._post("sendMessage", msg.model_dump(exclude_none=True))

    def _send_media(self, message: TelegramMedia) -> DeliveryResult:
        """Send a media message via sendPhoto/sendDocument/sendVideo."""
        endpoint = _MEDIA_TYPE_ENDPOINTS.get(message.media_type)
        if not endpoint:
            return DeliveryResult.fail(
                f"Unsupported media type: {message.media_type}",
                error_code="unsupported_media_type",
            )

        msg = TelegramMediaPayload.model_validate(
            {
                "chat_id": message.chat_id,
                message.media_type: message.media_url,
                "caption": message.caption,
                "parse_mode": message.parse_mode,
            }
        )
        return self._post(endpoint, msg.model_dump(exclude_none=True))

    def _post(self, method: str, payload: dict[str, Any]) -> DeliveryResult:
        """Make a POST request to the Telegram Bot API."""
        url = f"{self._base_url}/{method}"
        try:
            response = self._client.post(url, json=payload)
            data = response.json()

            if data.get("ok"):
                success_resp = TelegramSuccessResponse.model_validate(data)
                external_id = str(success_resp.result.message_id)
                logger.info("Telegram message sent via %s, message_id=%s", method, external_id)
                return DeliveryResult.ok(status=DeliveryStatus.SENT, external_id=external_id)

            error_resp = TelegramErrorResponse.model_validate(data)
            error_code = str(error_resp.error_code)
            logger.error("Telegram API error: [%s] %s", error_code, error_resp.description)
            return DeliveryResult.fail(error_resp.description, error_code=error_code)

        except ValidationError as exc:
            logger.exception("Failed to validate Telegram API response")
            return DeliveryResult.fail(f"Invalid Telegram API response: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error calling Telegram Bot API")
            return DeliveryResult.fail(str(exc))
