"""SMTP2GO email provider."""

from __future__ import annotations

import asyncio
import logging

from typing import Any

import httpx

from messaging.types import DeliveryResult, DeliveryStatus, EmailMessage, Smtp2GoConfig

logger = logging.getLogger(__name__)

SMTP2GO_API_URL = "https://api.smtp2go.com/v3/email/send"
DEFAULT_TIMEOUT_SECONDS = 10.0


class Smtp2GoProvider:
    """Sends emails via the SMTP2GO REST API."""

    def __init__(self, config: Smtp2GoConfig) -> None:
        self._api_key = config.api_key
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> Smtp2GoProvider:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def send(self, message: EmailMessage) -> DeliveryResult:
        """Send an email via SMTP2GO."""
        sender = f"{message.from_name} <{message.from_email}>" if message.from_name else message.from_email
        payload = {
            "sender": sender,
            "to": [message.to],
            "subject": message.subject,
            "html_body": message.html_content,
        }
        try:
            response = self._client.post(
                SMTP2GO_API_URL,
                json=payload,
                headers={"X-Smtp2go-Api-Key": self._api_key},
            )
            if 200 <= response.status_code < 300:
                logger.info("Email sent via SMTP2GO to %s", message.to)
                return DeliveryResult.ok(status=DeliveryStatus.SENT)
            logger.error(
                "SMTP2GO send failed. Status: %s, Body: %s",
                response.status_code,
                response.text,
            )
            return DeliveryResult.fail(
                f"SMTP2GO returned status {response.status_code}",
                error_code=str(response.status_code),
            )
        except Exception as exc:
            logger.exception("Unexpected error sending email via SMTP2GO")
            return DeliveryResult.fail(str(exc))

    async def send_async(self, message: EmailMessage) -> DeliveryResult:
        """Send an email asynchronously (runs sync send in a thread)."""
        return await asyncio.to_thread(self.send, message)
