"""Mock messaging provider for testing.

Records all sent messages and returns configurable results.
Useful for unit testing code that depends on messaging without
hitting real providers.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from .types import DeliveryResult, DeliveryStatus, Message


@dataclass
class SentMessage:
    """Record of a message sent through the MockProvider."""

    message: Message
    result: DeliveryResult


class MockProvider:
    """Test provider that records messages and returns configurable results.

    Usage::

        provider = MockProvider()
        result = provider.send(WhatsAppText(to="+5511...", body="hi"))
        assert result.succeeded
        assert len(provider.sent) == 1
        assert provider.sent[0].message.body == "hi"

    Configure failures::

        provider = MockProvider(failure_rate=0.5)
        # ~50% of sends will return FAILED

    Or provide a fixed result::

        provider = MockProvider(fixed_result=DeliveryResult.fail("quota exceeded"))
        result = provider.send(...)
        assert not result.succeeded
    """

    def __init__(
        self,
        *,
        failure_rate: float = 0.0,
        fixed_result: DeliveryResult | None = None,
    ) -> None:
        self.failure_rate = failure_rate
        self.fixed_result = fixed_result
        self.sent: list[SentMessage] = []

    def send(self, message: Message) -> DeliveryResult:
        if self.fixed_result is not None:
            result = self.fixed_result
        elif self.failure_rate > 0 and random.random() < self.failure_rate:  # noqa: S311
            result = DeliveryResult.fail("Simulated failure")
        else:
            result = DeliveryResult.ok(
                status=DeliveryStatus.SENT,
                external_id=f"mock_{uuid.uuid4().hex[:12]}",
            )

        self.sent.append(SentMessage(message=message, result=result))
        return result

    def fetch_status(self, external_id: str) -> DeliveryResult | None:
        for record in self.sent:
            if record.result.external_id == external_id:
                return record.result
        return None

    def reset(self) -> None:
        """Clear all recorded messages."""
        self.sent.clear()
