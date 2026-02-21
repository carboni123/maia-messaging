"""Twilio SMS provider."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from twilio.base.exceptions import TwilioRestException  # type: ignore[import-untyped]
from twilio.http.http_client import TwilioHttpClient  # type: ignore[import-untyped]
from twilio.rest import Client  # type: ignore[import-untyped]

from messaging.providers.twilio import _map_twilio_status
from messaging.types import DeliveryResult, SMSMessage, TwilioSMSConfig

logger = logging.getLogger(__name__)

MAX_SMS_CHARS = 1600
DEFAULT_TIMEOUT_SECONDS = 10.0


class TwilioSMSProvider:
    """Sends SMS messages via Twilio REST API."""

    def __init__(self, config: TwilioSMSConfig) -> None:
        if not config.from_number:
            raise ValueError("TwilioSMSConfig.from_number is required for SMS delivery")
        self._config = config
        http_client = TwilioHttpClient(timeout=DEFAULT_TIMEOUT_SECONDS)
        self._client = Client(config.account_sid, config.auth_token, http_client=http_client)

    def send(self, message: SMSMessage) -> DeliveryResult:
        """Send an SMS synchronously."""
        body = message.body.strip()
        if not body:
            return DeliveryResult.fail("No message body provided")

        if len(body) > MAX_SMS_CHARS:
            body = body[:MAX_SMS_CHARS]

        params: dict[str, Any] = {
            "to": message.to,
            "from_": self._config.from_number,
            "body": body,
        }
        if self._config.status_callback:
            params["status_callback"] = self._config.status_callback

        return self._create_message(params)

    async def send_async(self, message: SMSMessage) -> DeliveryResult:
        """Send an SMS asynchronously (runs sync send in a thread)."""
        return await asyncio.to_thread(self.send, message)

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        """Poll Twilio for current SMS delivery status."""
        try:
            msg = self._client.messages(external_id).fetch()
            status = _map_twilio_status(getattr(msg, "status", None))
            return DeliveryResult(
                status=status,
                external_id=msg.sid,
                error_code=str(msg.error_code) if msg.error_code else None,
                error_message=msg.error_message,
            )
        except TwilioRestException as exc:
            logger.error("Failed to fetch SMS status for %s: %s", external_id, exc)
            return DeliveryResult.fail(str(exc.msg), error_code=str(exc.code) if exc.code else None)
        except Exception as exc:
            logger.error("Failed to fetch SMS status for %s: %s", external_id, exc)
            return None

    def _create_message(self, params: dict[str, Any]) -> DeliveryResult:
        try:
            msg = self._client.messages.create(**params)
            status = _map_twilio_status(getattr(msg, "status", None))
            return DeliveryResult(
                status=status,
                external_id=getattr(msg, "sid", None),
                error_code=str(msg.error_code) if getattr(msg, "error_code", None) else None,
                error_message=getattr(msg, "error_message", None),
            )
        except TwilioRestException as exc:
            logger.error("Twilio SMS API error: code=%s msg=%s", exc.code, exc.msg)
            return DeliveryResult.fail(str(exc.msg), error_code=str(exc.code) if exc.code else None)
        except Exception as exc:
            logger.error("Twilio SMS send failed: %s", exc)
            return DeliveryResult.fail(str(exc))
