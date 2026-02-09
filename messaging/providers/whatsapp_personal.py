"""WhatsApp Personal messaging provider via WWjs adapter."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests

from messaging.types import (
    DeliveryResult,
    DeliveryStatus,
    Message,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppTemplate,
    WhatsAppText,
)

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 1532
REQUEST_TIMEOUT_SECONDS = 15


class AdapterRequestError(RuntimeError):
    """Error raised when communication with the adapter fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class _AdapterTextResponse:
    """Parsed response from /api/sendText."""

    message_id: str | None
    error: str | None


@dataclass(frozen=True)
class _AdapterMediaResponse:
    """Parsed response from media endpoints."""

    message_id: str | None
    error: str | None


class WhatsAppPersonalProvider:
    """Sends WhatsApp messages via the WWjs adapter HTTP API."""

    def __init__(self, config: WhatsAppPersonalConfig) -> None:
        self._config = config
        self._base_url = config.adapter_base_url.rstrip("/")

    def send(self, message: Message) -> DeliveryResult:
        """Send a message synchronously."""
        if isinstance(message, WhatsAppText):
            return self._send_text(message)
        if isinstance(message, WhatsAppMedia):
            return self._send_media(message)
        if isinstance(message, WhatsAppTemplate):
            return DeliveryResult.fail("WhatsApp Personal does not support template messages")
        return DeliveryResult.fail(f"Unsupported message type: {type(message).__name__}")

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """WhatsApp Personal adapter does not support status polling."""
        return None

    # ── Private dispatch ──────────────────────────────────────────

    def _send_text(self, message: WhatsAppText) -> DeliveryResult:
        body = message.body.strip()
        if not body:
            return DeliveryResult.fail("Cannot send an empty message")

        if len(body) > MAX_BODY_CHARS:
            return DeliveryResult.fail(f"Message text exceeds {MAX_BODY_CHARS} characters")

        chat_id = _normalize_chat_id(message.to)
        if chat_id is None:
            return DeliveryResult.fail("Invalid phone number")

        payload = {"chatId": chat_id, "text": body}

        try:
            resp_data = self._post("/api/sendText", payload)
        except AdapterRequestError as exc:
            return DeliveryResult.fail(str(exc))

        parsed = _parse_send_text_response(resp_data)
        if parsed.error:
            return DeliveryResult.fail(parsed.error)

        return DeliveryResult.ok(
            status=DeliveryStatus.SENT,
            external_id=parsed.message_id,
        )

    def _send_media(self, message: WhatsAppMedia) -> DeliveryResult:
        if not message.media_urls:
            return DeliveryResult.fail("No media URLs provided")

        chat_id = _normalize_chat_id(message.to)
        if chat_id is None:
            return DeliveryResult.fail("Invalid phone number")

        errors: list[str] = []
        external_id: str | None = None

        # Send text body first if present and we have media
        text_sent = False
        if message.caption and message.caption.strip():
            text_payload = {"chatId": chat_id, "text": message.caption.strip()}
            try:
                resp_data = self._post("/api/sendText", text_payload)
                parsed = _parse_send_text_response(resp_data)
                if parsed.error:
                    errors.append(parsed.error)
                elif parsed.message_id:
                    external_id = parsed.message_id
                    text_sent = True
            except AdapterRequestError as exc:
                errors.append(str(exc))

        for idx, url in enumerate(message.media_urls):
            mimetype = message.media_types[idx] if idx < len(message.media_types) else "application/octet-stream"
            filename = message.media_filenames[idx] if idx < len(message.media_filenames) else None
            kind = _map_mime_to_kind(mimetype)
            endpoint = _kind_to_endpoint(kind)

            # Only attach caption to first media if we haven't sent text separately
            caption = message.caption if not text_sent and idx == 0 else None

            file_payload: dict[str, str | None] = {"mimetype": mimetype, "url": url}
            if filename:
                file_payload["filename"] = filename

            request_payload: dict[str, object] = {"chatId": chat_id, "file": file_payload}
            if caption:
                request_payload["caption"] = caption

            try:
                resp_data = self._post(f"/api/{endpoint}", request_payload)
            except AdapterRequestError as exc:
                errors.append(str(exc))
                continue

            parsed_media = _parse_send_media_response(resp_data)
            if parsed_media.error:
                errors.append(parsed_media.error)
                continue

            if parsed_media.message_id and not external_id:
                external_id = parsed_media.message_id

        if errors and not external_id:
            return DeliveryResult.fail("; ".join(errors))

        return DeliveryResult(
            status=DeliveryStatus.FAILED if errors else DeliveryStatus.SENT,
            external_id=external_id,
            error_message="; ".join(errors) if errors else None,
        )

    # ── HTTP helpers ──────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._config.api_key, "Content-Type": "application/json"}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else None
            detail = response.text if response is not None else str(exc)
            raise AdapterRequestError(
                f"Adapter error ({status_code or 'unknown'}): {detail}",
                status_code=status_code,
            ) from exc
        except requests.RequestException as exc:
            raise AdapterRequestError("Network error communicating with adapter") from exc

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise AdapterRequestError(f"Adapter returned unexpected content type: {content_type}")

        try:
            data = response.json()
        except ValueError as exc:
            raise AdapterRequestError("Adapter returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise AdapterRequestError("Adapter returned non-object JSON")
        return data


# ── Helpers ───────────────────────────────────────────────────────


def _normalize_chat_id(phone_number: str) -> str | None:
    """Normalize a phone number to a WhatsApp chat ID."""
    trimmed = phone_number.strip()

    # Group JID passthrough
    if trimmed.endswith("@g.us"):
        return trimmed

    # Strip whatsapp: prefix if present
    if trimmed.lower().startswith("whatsapp:"):
        trimmed = trimmed[9:]

    # Allow formatted numbers like "+55 (11) 99999-9999"
    digits_only = "".join(ch for ch in trimmed if ch.isdigit())
    if not digits_only or digits_only.startswith("0"):
        return None

    candidate = f"+{digits_only}"

    if not re.fullmatch(r"\+[1-9]\d{1,14}", candidate):
        return None

    return candidate


def _map_mime_to_kind(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "voice"
    return "document"


def _kind_to_endpoint(kind: str) -> str:
    return {
        "image": "sendImage",
        "document": "sendFile",
        "voice": "sendVoice",
        "video": "sendVideo",
    }.get(kind, "sendFile")


def _parse_send_text_response(data: dict[str, Any]) -> _AdapterTextResponse:
    """Parse the adapter's sendText response into a structured object."""
    adapter_error = _extract_adapter_error(data)
    if adapter_error:
        return _AdapterTextResponse(message_id=None, error=adapter_error)

    payload = data.get("payload")
    if isinstance(payload, Mapping):
        message_sid = payload.get("MessageSid") or payload.get("Sid")
        if isinstance(message_sid, str) and message_sid.strip():
            return _AdapterTextResponse(message_id=message_sid, error=None)

    return _AdapterTextResponse(message_id=None, error="Adapter response missing message id")


def _parse_send_media_response(data: dict[str, Any]) -> _AdapterMediaResponse:
    """Parse adapter media response into structured result."""
    adapter_error = _extract_adapter_error(data)
    if adapter_error:
        return _AdapterMediaResponse(message_id=None, error=adapter_error)

    message_id = _extract_message_id(data)
    if message_id:
        return _AdapterMediaResponse(message_id=message_id, error=None)

    return _AdapterMediaResponse(message_id=None, error="Adapter response missing message id")


def _extract_adapter_error(data: Mapping[str, Any]) -> str | None:
    """Extract adapter error message when returned in JSON payload.

    Only checks ``"error"`` and ``"detail"`` at the top level.
    ``"message"`` is only checked inside nested error/detail objects
    to avoid false-positives on success responses that carry a
    top-level ``"message"`` field.
    """
    for key in ("error", "detail"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            for nested_key in ("message", "detail", "error"):
                nested = value.get(nested_key)
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()

    return None


def _extract_message_id(data: dict[str, Any]) -> str | None:
    """Extract message ID from an adapter media response."""
    raw_id = data.get("id")
    if isinstance(raw_id, dict):
        nested_id = raw_id.get("_serialized") or raw_id.get("id")
        if isinstance(nested_id, str) and nested_id.strip():
            return nested_id.strip()
        return None
    if isinstance(raw_id, str):
        return raw_id.strip() or None

    payload = data.get("payload")
    if isinstance(payload, Mapping):
        message_sid = payload.get("MessageSid") or payload.get("Sid")
        if isinstance(message_sid, str) and message_sid.strip():
            return message_sid.strip()

    return None
