"""Tests for the MessagingGateway."""

from messaging import (
    DeliveryResult,
    MessagingGateway,
    MockProvider,
    WhatsAppText,
)


class TestGatewaySend:
    def test_send_text_success(self, mock_provider: MockProvider):
        gateway = MessagingGateway(mock_provider)
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        result = gateway.send(msg)
        assert result.succeeded
        assert len(mock_provider.sent) == 1

    def test_send_returns_provider_failure(self):
        provider = MockProvider(fixed_result=DeliveryResult.fail("quota exceeded"))
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        result = gateway.send(msg)
        assert not result.succeeded
        assert result.error_message == "quota exceeded"


class TestPhoneFallback:
    def test_fallback_on_invalid_number(self):
        """When provider fails with 'invalid number', retry with 8-digit format."""
        call_count = 0
        results = [
            DeliveryResult.fail("The number is not a valid WhatsApp user"),
            DeliveryResult.ok(external_id="SM_fallback"),
        ]

        class FallbackProvider:
            def send(self, message):
                nonlocal call_count
                result = results[call_count]
                call_count += 1
                return result

            def fetch_status(self, external_id):
                return None

        gateway = MessagingGateway(FallbackProvider())
        # 9-digit Brazilian number
        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert result.succeeded
        assert result.external_id == "SM_fallback"
        assert result.used_fallback_number == "whatsapp:+555198644323"
        assert call_count == 2

    def test_no_fallback_when_disabled(self):
        """When phone_fallback=False, don't retry."""
        provider = MockProvider(fixed_result=DeliveryResult.fail("not a valid whatsapp"))
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=False)

        assert not result.succeeded
        assert result.used_fallback_number is None
        assert len(provider.sent) == 1

    def test_no_fallback_when_error_is_not_invalid_number(self):
        """Don't retry on non-phone errors."""
        provider = MockProvider(fixed_result=DeliveryResult.fail("rate limit exceeded"))
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        assert len(provider.sent) == 1

    def test_fallback_both_fail(self):
        """When both formats fail, return original failure."""
        provider = MockProvider(fixed_result=DeliveryResult.fail("not a valid whatsapp"))
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        # Should have tried both formats
        assert len(provider.sent) == 2
        assert result.used_fallback_number is None

    def test_no_fallback_for_non_brazilian(self):
        """Non-Brazilian numbers don't have an alternate format."""
        provider = MockProvider(fixed_result=DeliveryResult.fail("not a valid whatsapp"))
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+14155238886", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        # Only one attempt (no Brazilian fallback possible)
        assert len(provider.sent) == 1


class TestFetchStatus:
    def test_delegates_to_provider(self, mock_provider: MockProvider):
        gateway = MessagingGateway(mock_provider)
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hi")
        send_result = gateway.send(msg)
        ext_id = send_result.external_id

        status = gateway.fetch_status(ext_id)
        assert status is not None
        assert status.succeeded

    def test_returns_none_for_unknown_id(self, mock_provider: MockProvider):
        gateway = MessagingGateway(mock_provider)
        assert gateway.fetch_status("unknown_id") is None
