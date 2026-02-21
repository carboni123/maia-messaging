"""Tests for the Twilio SMS provider."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from messaging import DeliveryStatus, SMSMessage, TwilioSMSConfig
from messaging.sms.twilio import TwilioSMSProvider


def _make_provider(config: TwilioSMSConfig) -> TwilioSMSProvider:
    """Create a TwilioSMSProvider with a mocked Client."""
    with patch("messaging.sms.twilio.Client"), \
         patch("messaging.sms.twilio.TwilioHttpClient"):
        return TwilioSMSProvider(config)


class TestTwilioSMSSend:
    def test_send_sms_success(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        result = provider.send(SMSMessage(to="+5511999999999", body="Hello via SMS"))

        assert result.succeeded
        assert result.external_id == "SM123"
        assert result.status == DeliveryStatus.SENT
        provider._client.messages.create.assert_called_once()
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["body"] == "Hello via SMS"
        assert call_kwargs.kwargs["to"] == "+5511999999999"
        assert call_kwargs.kwargs["from_"] == "+14155238886"

    def test_send_sms_empty_body(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        result = provider.send(SMSMessage(to="+5511999999999", body="  "))
        assert not result.succeeded
        assert "No message body" in (result.error_message or "")

    def test_send_sms_truncates_long_body(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        long_body = "x" * 2000
        provider.send(SMSMessage(to="+5511999999999", body=long_body))

        call_kwargs = provider._client.messages.create.call_args
        assert len(call_kwargs.kwargs["body"]) == 1600


class TestTwilioSMSErrorHandling:
    def test_twilio_rest_exception(self, twilio_sms_config: TwilioSMSConfig):
        from twilio.base.exceptions import TwilioRestException

        provider = _make_provider(twilio_sms_config)
        provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(
                400, "https://api.twilio.com", msg="Invalid 'To' Phone Number", code=21211
            )
        )

        result = provider.send(SMSMessage(to="+invalid", body="Hi"))
        assert not result.succeeded
        assert result.error_code == "21211"
        assert "Invalid" in (result.error_message or "")

    def test_generic_exception(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        provider._client.messages.create = MagicMock(side_effect=ConnectionError("timeout"))

        result = provider.send(SMSMessage(to="+5511999999999", body="Hi"))
        assert not result.succeeded
        assert "timeout" in (result.error_message or "")


class TestTwilioSMSStatusCallback:
    def test_status_callback_included(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        provider.send(SMSMessage(to="+5511999999999", body="Hello"))
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["status_callback"] == "https://example.com/webhook/sms-status"

    def test_no_status_callback_when_none(self):
        config = TwilioSMSConfig(
            account_sid="AC123",
            auth_token="token",
            from_number="+14155238886",
            status_callback=None,
        )
        provider = _make_provider(config)
        mock_msg = MagicMock(sid="SM123", status="sent", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        provider.send(SMSMessage(to="+5511999999999", body="Hello"))
        call_kwargs = provider._client.messages.create.call_args
        assert "status_callback" not in call_kwargs.kwargs


class TestTwilioSMSFetchStatus:
    def test_fetch_status_success(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        mock_msg = MagicMock(sid="SM123", status="delivered", error_code=None, error_message=None)
        provider._client.messages = MagicMock(return_value=MagicMock(fetch=MagicMock(return_value=mock_msg)))

        result = provider.fetch_status("SM123")
        assert result is not None
        assert result.status == DeliveryStatus.DELIVERED

    def test_fetch_status_twilio_error(self, twilio_sms_config: TwilioSMSConfig):
        from twilio.base.exceptions import TwilioRestException

        provider = _make_provider(twilio_sms_config)
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

    def test_fetch_status_unknown_error_returns_none(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        provider._client.messages = MagicMock(
            return_value=MagicMock(
                fetch=MagicMock(side_effect=RuntimeError("unexpected"))
            )
        )

        result = provider.fetch_status("SM123")
        assert result is None


class TestTwilioSMSAsync:
    def test_send_async(self, twilio_sms_config: TwilioSMSConfig):
        provider = _make_provider(twilio_sms_config)
        mock_msg = MagicMock(sid="SM123", status="queued", error_code=None, error_message=None)
        provider._client.messages.create = MagicMock(return_value=mock_msg)

        result = asyncio.run(
            provider.send_async(SMSMessage(to="+5511999999999", body="Async SMS"))
        )
        assert result.succeeded
        assert result.external_id == "SM123"


class TestTwilioSMSInit:
    def test_validates_from_number(self):
        with pytest.raises(ValueError, match="from_number"):
            with patch("messaging.sms.twilio.Client"), \
                 patch("messaging.sms.twilio.TwilioHttpClient"):
                TwilioSMSProvider(TwilioSMSConfig(
                    account_sid="AC123",
                    auth_token="token",
                    from_number="",
                ))
