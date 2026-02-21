"""SendGrid email provider."""

from __future__ import annotations

import asyncio
import logging

from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]
from sendgrid.helpers.mail import Mail  # type: ignore[import-untyped]

from messaging.types import DeliveryResult, DeliveryStatus, EmailMessage, SendGridConfig

logger = logging.getLogger(__name__)


class SendGridProvider:
    """Sends emails via the SendGrid API."""

    def __init__(self, config: SendGridConfig) -> None:
        self._client = SendGridAPIClient(config.api_key)

    def send(self, message: EmailMessage) -> DeliveryResult:
        """Send an email via SendGrid."""
        mail = Mail(
            from_email=(message.from_email, message.from_name) if message.from_name else message.from_email,
            to_emails=message.to,
            subject=message.subject,
            html_content=message.html_content,
        )
        try:
            response = self._client.send(mail)
            if 200 <= response.status_code < 300:
                logger.info("Email sent via SendGrid to %s", message.to)
                return DeliveryResult.ok(status=DeliveryStatus.SENT)
            logger.error(
                "SendGrid send failed. Status: %s, Body: %s",
                response.status_code,
                response.body,
            )
            return DeliveryResult.fail(
                f"SendGrid returned status {response.status_code}",
                error_code=str(response.status_code),
            )
        except Exception as exc:
            logger.exception("Unexpected error sending email via SendGrid")
            return DeliveryResult.fail(str(exc))

    async def send_async(self, message: EmailMessage) -> DeliveryResult:
        """Send an email asynchronously (runs sync send in a thread)."""
        return await asyncio.to_thread(self.send, message)
