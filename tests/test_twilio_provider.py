"""Tests for the Twilio provider."""

from unittest.mock import MagicMock, patch

from messaging import DeliveryStatus, TwilioConfig, WhatsAppMedia, WhatsAppTemplate, WhatsAppText
from messaging.providers.twilio import TwilioProvider, empty_messaging_response_xml


def _make_provider(config: TwilioConfig) -> TwilioProvider:
    """Create a TwilioProvider with a mocked Client."""
    with patch("messaging.providers.twilio.Client"):
        return TwilioProvider(config)


class TestTwilioSendText:
    def test_send_text_success(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))

        assert result.succeeded
        assert result.external_id == "SM123"
        assert result.status == DeliveryStatus.SENT
        provider._client.messages.create.assert_called_once()
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["body"] == "Hello"
        assert call_kwargs.kwargs["to"] == "whatsapp:+5511999999999"

    def test_send_empty_text_fails(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="  "))
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_text_truncates_long_body(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        long_body = "x" * 2000
        provider.send(WhatsAppText(to="whatsapp:+5511999999999", body=long_body))

        call_kwargs = provider._client.messages.create.call_args
        assert len(call_kwargs.kwargs["body"]) == 1532

    def test_unknown_status_is_treated_as_failed(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="new_unknown_status", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))

        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED


class TestTwilioSendMedia:
    def test_send_media_success(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM456", status="queued", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        msg = WhatsAppMedia(
            to="whatsapp:+5511999999999",
            media_urls=["https://example.com/file.pdf"],
            caption="Report",
        )
        result = provider.send(msg)

        assert result.succeeded
        assert result.status == DeliveryStatus.QUEUED
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["media_url"] == ["https://example.com/file.pdf"]
        assert call_kwargs.kwargs["body"] == "Report"

    def test_send_media_no_urls_fails(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        result = provider.send(WhatsAppMedia(to="whatsapp:+5511999999999"))
        assert not result.succeeded
        assert "No media URLs" in result.error_message


class TestTwilioSendTemplate:
    def test_send_template_success(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM789", status="accepted", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        msg = WhatsAppTemplate(
            to="whatsapp:+5511999999999",
            content_sid="HX123",
            content_variables={"1": "John"},
        )
        result = provider.send(msg)

        assert result.succeeded
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["content_sid"] == "HX123"
        assert '"1": "John"' in call_kwargs.kwargs["content_variables"]


class TestTwilioErrorHandling:
    def test_twilio_rest_exception(self, twilio_config: TwilioConfig):
        from twilio.base.exceptions import TwilioRestException

        provider = _make_provider(twilio_config)
        provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(
                400, "https://api.twilio.com", msg="Invalid 'To' Phone Number", code=21211
            )
        )

        result = provider.send(WhatsAppText(to="whatsapp:+invalid", body="Hi"))
        assert not result.succeeded
        assert result.error_code == "21211"
        assert "Invalid" in result.error_message

    def test_generic_exception(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        provider._client.messages.create = MagicMock(side_effect=ConnectionError("timeout"))

        result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hi"))
        assert not result.succeeded
        assert "timeout" in result.error_message


class TestTwilioStatusCallback:
    def test_status_callback_included(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["status_callback"] == "https://example.com/webhook/status"

    def test_no_status_callback_when_none(self):
        config = TwilioConfig(
            account_sid="AC123",
            auth_token="token",
            whatsapp_number="whatsapp:+14155238886",
            status_callback=None,
        )
        provider = _make_provider(config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))
        call_kwargs = provider._client.messages.create.call_args
        assert "status_callback" not in call_kwargs.kwargs


class TestTwilioFetchStatus:
    def test_fetch_status_success(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="delivered", error_code=None, error_message=None)
        provider._client.messages = MagicMock(return_value=MagicMock(fetch=MagicMock(return_value=mock_msg)))

        result = provider.fetch_status("SM123")
        assert result is not None
        assert result.status == DeliveryStatus.DELIVERED

    def test_fetch_status_not_found(self, twilio_config: TwilioConfig):
        from twilio.base.exceptions import TwilioRestException

        provider = _make_provider(twilio_config)
        provider._client.messages = MagicMock(
            return_value=MagicMock(
                fetch=MagicMock(
                    side_effect=TwilioRestException(20404, "https://api.twilio.com", msg="Message not found")
                )
            )
        )

        result = provider.fetch_status("SM_nonexistent")
        assert result is not None
        assert not result.succeeded

    def test_fetch_status_canceled_maps_to_failed(self, twilio_config: TwilioConfig):
        provider = _make_provider(twilio_config)
        mock_msg = MagicMock(sid="SM123", status="canceled", error_code=None, error_message=None)
        provider._client.messages = MagicMock(return_value=MagicMock(fetch=MagicMock(return_value=mock_msg)))

        result = provider.fetch_status("SM123")
        assert result is not None
        assert result.status == DeliveryStatus.FAILED
        assert not result.succeeded


class TestEmptyMessagingResponseXml:
    def test_returns_xml_string(self):
        xml = empty_messaging_response_xml()
        assert isinstance(xml, str)
        assert "Response" in xml

    def test_is_valid_twiml(self):
        xml = empty_messaging_response_xml()
        assert xml.startswith("<?xml")

    def test_is_cached(self):
        """Verify lru_cache returns the same object."""
        a = empty_messaging_response_xml()
        b = empty_messaging_response_xml()
        assert a is b
