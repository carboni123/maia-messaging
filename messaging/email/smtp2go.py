"""SMTP2GO email provider."""

from __future__ import annotations

import logging

import httpx

from messaging.types import DeliveryResult, DeliveryStatus, EmailMessage, Smtp2GoConfig

logger = logging.getLogger(__name__)

SMTP2GO_API_URL = "https://api.smtp2go.com/v3/email/send"


class Smtp2GoProvider:
    """Sends emails via the SMTP2GO REST API."""

    def __init__(self, config: Smtp2GoConfig) -> None:
        self._api_key = config.api_key

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
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
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
