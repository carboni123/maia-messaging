"""Tests for core types."""

import pytest

from messaging import (
    DeliveryResult,
    DeliveryStatus,
    GatewayResult,
    MetaWhatsAppTemplate,
    SMSMessage,
    TelegramMedia,
    TelegramText,
    WhatsAppMedia,
    WhatsAppTemplate,
    WhatsAppText,
)


class TestDeliveryResult:
    def test_ok_factory(self):
        result = DeliveryResult.ok(external_id="SM123")
        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "SM123"
        assert result.error_message is None

    def test_fail_factory(self):
        result = DeliveryResult.fail("Something broke", error_code="21211")
        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED
        assert result.error_message == "Something broke"
        assert result.error_code == "21211"

    def test_succeeded_for_various_statuses(self):
        assert DeliveryResult(status=DeliveryStatus.QUEUED).succeeded
        assert DeliveryResult(status=DeliveryStatus.SENT).succeeded
        assert DeliveryResult(status=DeliveryStatus.DELIVERED).succeeded
        assert DeliveryResult(status=DeliveryStatus.READ).succeeded
        assert not DeliveryResult(status=DeliveryStatus.FAILED).succeeded
        assert not DeliveryResult(status=DeliveryStatus.UNDELIVERED).succeeded


class TestDeliveryStatusPrecedence:
    def test_positive_statuses_are_ordered(self):
        assert DeliveryStatus.QUEUED.precedence < DeliveryStatus.SENT.precedence
        assert DeliveryStatus.SENT.precedence < DeliveryStatus.DELIVERED.precedence
        assert DeliveryStatus.DELIVERED.precedence < DeliveryStatus.READ.precedence

    def test_failure_statuses_are_negative(self):
        assert DeliveryStatus.FAILED.precedence < 0
        assert DeliveryStatus.UNDELIVERED.precedence < 0

    def test_all_statuses_have_precedence(self):
        for status in DeliveryStatus:
            assert isinstance(status.precedence, int)

    def test_precedence_matches_app_convention(self):
        """Verify the library precedence matches the app's STATUS_PRECEDENCE map."""
        assert DeliveryStatus.QUEUED.precedence == 1
        assert DeliveryStatus.SENT.precedence == 4
        assert DeliveryStatus.DELIVERED.precedence == 5
        assert DeliveryStatus.READ.precedence == 6
        assert DeliveryStatus.FAILED.precedence == -1
        assert DeliveryStatus.UNDELIVERED.precedence == -2

    def test_can_compare_statuses_via_precedence(self):
        """Demonstrates how consumers would compare status progression."""
        old = DeliveryStatus.QUEUED
        new = DeliveryStatus.DELIVERED
        assert new.precedence > old.precedence  # Status progressed


class TestGatewayResult:
    def test_proxies_delivery_fields(self):
        delivery = DeliveryResult.ok(external_id="SM456")
        result = GatewayResult(delivery=delivery, used_fallback_number="+555198644323")
        assert result.succeeded
        assert result.external_id == "SM456"
        assert result.used_fallback_number == "+555198644323"

    def test_no_fallback(self):
        delivery = DeliveryResult.fail("error")
        result = GatewayResult(delivery=delivery)
        assert not result.succeeded
        assert result.used_fallback_number is None


class TestMessageTypes:
    def test_whatsapp_text(self):
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        assert msg.to == "whatsapp:+5511999999999"
        assert msg.body == "Hello"

    def test_whatsapp_media(self):
        msg = WhatsAppMedia(
            to="whatsapp:+5511999999999",
            media_urls=["https://example.com/file.pdf"],
            caption="Report",
        )
        assert len(msg.media_urls) == 1
        assert msg.caption == "Report"

    def test_whatsapp_template(self):
        msg = WhatsAppTemplate(
            to="whatsapp:+5511999999999",
            content_sid="HX123",
            content_variables={"1": "John"},
        )
        assert msg.content_sid == "HX123"
        assert msg.content_variables == {"1": "John"}

    def test_meta_whatsapp_template(self):
        msg = MetaWhatsAppTemplate(
            to="+5511999999999",
            template_name="order_update",
            language_code="pt_BR",
            components=[{"type": "body", "parameters": [{"type": "text", "text": "John"}]}],
        )
        assert msg.template_name == "order_update"
        assert msg.language_code == "pt_BR"
        assert len(msg.components) == 1

    def test_sms_message(self):
        msg = SMSMessage(to="+5511999999999", body="Your code is 123456")
        assert msg.to == "+5511999999999"
        assert msg.body == "Your code is 123456"

    def test_telegram_text(self):
        msg = TelegramText(chat_id=12345, body="Hello", parse_mode="HTML")
        assert msg.chat_id == 12345
        assert msg.body == "Hello"
        assert msg.parse_mode == "HTML"

    def test_telegram_media(self):
        msg = TelegramMedia(
            chat_id=12345,
            media_url="https://example.com/photo.jpg",
            media_type="photo",
            caption="A photo",
        )
        assert msg.media_type == "photo"
        assert msg.caption == "A photo"


class TestFrozenDataclasses:
    """All message types and results are frozen — mutation should raise."""

    def test_delivery_result_is_frozen(self):
        result = DeliveryResult.ok(external_id="SM123")
        with pytest.raises(AttributeError):
            result.status = DeliveryStatus.FAILED  # type: ignore[misc]

    def test_whatsapp_text_is_frozen(self):
        msg = WhatsAppText(to="+5511999999999", body="Hello")
        with pytest.raises(AttributeError):
            msg.body = "Mutated"  # type: ignore[misc]

    def test_gateway_result_is_frozen(self):
        result = GatewayResult(delivery=DeliveryResult.ok())
        with pytest.raises(AttributeError):
            result.used_fallback_number = "+5511"  # type: ignore[misc]
