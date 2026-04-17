"""Integration tests — full flow from message ingestion to delivery result.

These tests wire real library components together and only mock the
external transport boundary (Twilio SDK / HTTP adapter). They verify that
a message enters the gateway, flows through the provider, hits the
external API with the correct payload, and returns a correctly mapped result.

Unlike unit tests (which mock internal classes), these catch integration
issues like mismatched field names, broken status mapping chains, or
phone normalization not being applied before the API call.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from twilio.base.exceptions import TwilioRestException

from messaging import (
    DeliveryStatus,
    MessagingGateway,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    SMSMessage,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
    TwilioConfig,
    TwilioSMSConfig,
    WhatsAppContacts,
    WhatsAppInteractiveCTA,
    WhatsAppInteractiveList,
    WhatsAppInteractiveReply,
    WhatsAppLocation,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppProduct,
    WhatsAppProductList,
    WhatsAppReaction,
    WhatsAppSticker,
    WhatsAppTemplate,
    WhatsAppText,
)
from messaging.providers.meta import MetaWhatsAppProvider
from messaging.providers.twilio import TwilioProvider
from messaging.providers.whatsapp_personal import WhatsAppPersonalProvider
from messaging.sms.twilio import TwilioSMSProvider
from messaging.telegram.bot_api import TelegramBotProvider


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def twilio_provider() -> TwilioProvider:
    """TwilioProvider with mocked Twilio SDK Client."""
    with patch("messaging.providers.twilio.Client"), patch("messaging.providers.twilio.TwilioHttpClient"):
        config = TwilioConfig(
            account_sid="ACtest",
            auth_token="secret",
            whatsapp_number="whatsapp:+14155238886",
            status_callback="https://app.example.com/webhook/status",
        )
        return TwilioProvider(config)


@pytest.fixture
def whatsapp_provider() -> WhatsAppPersonalProvider:
    """WhatsAppPersonalProvider that won't hit a real HTTP server."""
    config = WhatsAppPersonalConfig(
        session_public_id="sess_abc",
        api_key="key_xyz",
        adapter_base_url="http://adapter:3001",
    )
    return WhatsAppPersonalProvider(config)


def _twilio_msg(*, sid: str = "SM123", status: str = "sent") -> MagicMock:
    """Fake Twilio message response object."""
    m = MagicMock()
    m.sid = sid
    m.status = status
    m.error_code = None
    m.error_message = None
    return m


def _twilio_failed_msg(
    *, sid: str = "SM999", error_code: int = 21211, error_message: str = "Invalid 'To' Phone Number"
) -> MagicMock:
    m = MagicMock()
    m.sid = sid
    m.status = "failed"
    m.error_code = error_code
    m.error_message = error_message
    return m


# ── Twilio: Text message end-to-end ─────────────────────────────────


class TestTwilioTextE2E:
    """Full flow: WhatsAppText → Gateway → TwilioProvider → Twilio SDK → DeliveryResult."""

    def test_text_message_arrives_at_twilio_with_correct_params(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(return_value=_twilio_msg())
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello from integration test")
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "SM123"
        assert result.status == DeliveryStatus.SENT

        call_kwargs = twilio_provider._client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+5511999999999"
        assert call_kwargs["from_"] == "whatsapp:+14155238886"
        assert call_kwargs["body"] == "Hello from integration test"
        assert call_kwargs["status_callback"] == "https://app.example.com/webhook/status"

    def test_empty_body_rejected_before_hitting_api(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock()
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="   ")
        result = gateway.send(msg)

        assert not result.succeeded
        assert "No message body" in (result.error_message or "")
        twilio_provider._client.messages.create.assert_not_called()

    def test_long_body_truncated_at_boundary(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(return_value=_twilio_msg())
        gateway = MessagingGateway(twilio_provider)

        body = "A" * 2000
        msg = WhatsAppText(to="whatsapp:+5511999999999", body=body)
        gateway.send(msg)

        sent_body = twilio_provider._client.messages.create.call_args.kwargs["body"]
        assert len(sent_body) == 1532


# ── Twilio: Template message end-to-end ──────────────────────────────


class TestTwilioTemplateE2E:
    """Full flow: WhatsAppTemplate → Gateway → TwilioProvider → Twilio SDK."""

    def test_template_params_reach_twilio_api(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(return_value=_twilio_msg(status="accepted"))
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppTemplate(
            to="whatsapp:+5511999999999",
            content_sid="HXabc123",
            content_variables={"1": "John", "2": "Order #42"},
        )
        result = gateway.send(msg)

        assert result.succeeded
        # "accepted" maps to QUEUED in the Twilio status mapping
        assert result.status == DeliveryStatus.QUEUED

        call_kwargs = twilio_provider._client.messages.create.call_args.kwargs
        assert call_kwargs["content_sid"] == "HXabc123"
        variables = json.loads(call_kwargs["content_variables"])
        assert variables == {"1": "John", "2": "Order #42"}

    def test_template_twilio_error_returns_failure_with_code(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(400, "https://api.twilio.com", msg="Invalid Content SID", code=21408)
        )
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppTemplate(
            to="whatsapp:+5511999999999",
            content_sid="HXinvalid",
            content_variables={},
        )
        result = gateway.send(msg)

        assert not result.succeeded
        assert result.error_code == "21408"
        assert "Invalid Content SID" in (result.error_message or "")


# ── Twilio: Media message end-to-end ─────────────────────────────────


class TestTwilioMediaE2E:
    """Full flow: WhatsAppMedia → Gateway → TwilioProvider → Twilio SDK."""

    def test_media_with_caption_sends_both(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(return_value=_twilio_msg(status="queued"))
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppMedia(
            to="whatsapp:+5511999999999",
            media_urls=["https://cdn.example.com/report.pdf"],
            caption="Here is your report.",
        )
        result = gateway.send(msg)

        assert result.succeeded
        call_kwargs = twilio_provider._client.messages.create.call_args.kwargs
        assert call_kwargs["media_url"] == ["https://cdn.example.com/report.pdf"]
        assert call_kwargs["body"] == "Here is your report."

    def test_media_without_urls_rejected(self, twilio_provider: TwilioProvider):
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppMedia(to="whatsapp:+5511999999999", media_urls=[])
        result = gateway.send(msg)

        assert not result.succeeded
        assert "No media URLs" in (result.error_message or "")


# ── Twilio: Phone fallback integration ───────────────────────────────


class TestTwilioPhoneFallbackE2E:
    """Phone fallback with a real TwilioProvider (mocked SDK).

    This is the critical integration: Gateway detects "invalid number" from
    the provider, denormalizes the Brazilian phone, and retries.
    """

    def test_9digit_fails_8digit_succeeds(self, twilio_provider: TwilioProvider):
        """First send with 9-digit fails, gateway retries with 8-digit, succeeds."""
        call_number = 0

        def fake_create(**kwargs):
            nonlocal call_number
            call_number += 1
            if call_number == 1:
                # First call: 9-digit number → Twilio says invalid
                raise TwilioRestException(
                    400,
                    "https://api.twilio.com",
                    msg="The number +5551998644323 is not a valid WhatsApp user",
                    code=63016,
                )
            # Second call: 8-digit fallback → success
            return _twilio_msg(sid="SM_fallback")

        twilio_provider._client.messages.create = MagicMock(side_effect=fake_create)
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert result.succeeded
        assert result.external_id == "SM_fallback"
        assert result.used_fallback_number == "whatsapp:+555198644323"
        assert call_number == 2

        # Verify first call used 9-digit, second used 8-digit
        calls = twilio_provider._client.messages.create.call_args_list
        assert calls[0].kwargs["to"] == "whatsapp:+5551998644323"
        assert calls[1].kwargs["to"] == "whatsapp:+555198644323"

    def test_fallback_both_formats_fail(self, twilio_provider: TwilioProvider):
        """Both 9-digit and 8-digit fail → returns original failure."""
        twilio_provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(
                400,
                "https://api.twilio.com",
                msg="Invalid number",
                code=21211,
            )
        )
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        assert result.used_fallback_number is None
        assert twilio_provider._client.messages.create.call_count == 2

    def test_no_fallback_for_non_phone_error(self, twilio_provider: TwilioProvider):
        """Rate limit error should NOT trigger phone fallback."""
        twilio_provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(
                429,
                "https://api.twilio.com",
                msg="Rate limit exceeded",
                code=20429,
            )
        )
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5551998644323", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        # Should NOT retry
        assert twilio_provider._client.messages.create.call_count == 1

    def test_no_fallback_for_us_number(self, twilio_provider: TwilioProvider):
        """US number has no alternate format, so fallback is skipped."""
        twilio_provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(
                400,
                "https://api.twilio.com",
                msg="Invalid number",
                code=21211,
            )
        )
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+14155238886", body="Hello")
        result = gateway.send(msg, phone_fallback=True)

        assert not result.succeeded
        # Only one call — no alternate format for US numbers
        assert twilio_provider._client.messages.create.call_count == 1


# ── Twilio: Status polling integration ───────────────────────────────


class TestTwilioStatusPollE2E:
    """Gateway.fetch_status → TwilioProvider.fetch_status → Twilio SDK."""

    def test_delivered_status_maps_correctly(self, twilio_provider: TwilioProvider):
        mock_msg = MagicMock(sid="SM123", status="delivered", error_code=None, error_message=None)
        twilio_provider._client.messages = MagicMock(return_value=MagicMock(fetch=MagicMock(return_value=mock_msg)))
        gateway = MessagingGateway(twilio_provider)

        result = gateway.fetch_status("SM123")
        assert result is not None
        assert result.status == DeliveryStatus.DELIVERED
        assert result.external_id == "SM123"

    def test_failed_status_includes_error_details(self, twilio_provider: TwilioProvider):
        mock_msg = MagicMock(sid="SM456", status="failed", error_code=30007, error_message="Message expired")
        twilio_provider._client.messages = MagicMock(return_value=MagicMock(fetch=MagicMock(return_value=mock_msg)))
        gateway = MessagingGateway(twilio_provider)

        result = gateway.fetch_status("SM456")
        assert result is not None
        assert result.status == DeliveryStatus.FAILED
        assert result.error_code == "30007"
        assert result.error_message == "Message expired"

    def test_unknown_message_returns_error(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages = MagicMock(
            return_value=MagicMock(
                fetch=MagicMock(
                    side_effect=TwilioRestException(404, "https://api.twilio.com", msg="Resource not found")
                )
            )
        )
        gateway = MessagingGateway(twilio_provider)

        result = gateway.fetch_status("SM_nonexistent")
        assert result is not None
        assert not result.succeeded


# ── WhatsApp Personal: Text end-to-end ───────────────────────────────


class TestWhatsAppPersonalTextE2E:
    """Full flow: WhatsAppText → Gateway → WhatsAppPersonalProvider → HTTP adapter."""

    def test_text_reaches_adapter_with_correct_payload(self, whatsapp_provider: WhatsAppPersonalProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(
            return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value={"payload": {"MessageSid": "wamid.abc123"}}),
            )
        )
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppText(to="+5511999999999", body="Integration test message")
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.abc123"

        call_kwargs = mock_client.post.call_args
        assert "/api/sendText" in call_kwargs[0][0]
        sent_json = call_kwargs.kwargs["json"]
        assert sent_json["text"] == "Integration test message"
        assert sent_json["chatId"] == "+5511999999999"

    def test_adapter_error_propagates_as_failure(self, whatsapp_provider: WhatsAppPersonalProvider):
        mock_response = MagicMock(status_code=500, text="Internal Server Error")
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=httpx.Request("POST", "http://adapter:3001/api/sendText"),
            response=mock_response,
        )
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_response)
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppText(to="+5511999999999", body="Should fail")
        result = gateway.send(msg)

        assert not result.succeeded
        assert "500" in (result.error_message or "")


# ── WhatsApp Personal: Media end-to-end ──────────────────────────────


class TestWhatsAppPersonalMediaE2E:
    """Full flow: WhatsAppMedia → Gateway → WhatsAppPersonalProvider → HTTP adapter."""

    def test_media_sends_text_then_file_separately(self, whatsapp_provider: WhatsAppPersonalProvider):
        """With caption + media, adapter gets 2 calls: sendText then sendImage."""
        call_log: list[str] = []

        def fake_post(url, **kwargs):
            call_log.append(url)
            resp = MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
            )
            if "sendText" in url:
                resp.json = MagicMock(return_value={"payload": {"MessageSid": "text_id"}})
            else:
                resp.json = MagicMock(return_value={"id": {"_serialized": "media_id"}})
            return resp

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=fake_post)
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppMedia(
            to="+5511999999999",
            media_urls=["https://cdn.example.com/photo.jpg"],
            media_types=["image/jpeg"],
            media_filenames=["photo.jpg"],
            caption="Check this photo",
        )
        result = gateway.send(msg)

        assert result.succeeded
        # First call: sendText, second call: sendImage
        assert len(call_log) == 2
        assert "sendText" in call_log[0]
        assert "sendImage" in call_log[1]

    def test_multiple_media_files_each_get_their_own_call(self, whatsapp_provider: WhatsAppPersonalProvider):
        """Each media URL gets a separate adapter call with correct endpoint."""
        call_log: list[str] = []

        def fake_post(url, **kwargs):
            call_log.append(url)
            resp = MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
            )
            resp.json = MagicMock(return_value={"id": "msg_ok"})
            return resp

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=fake_post)
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppMedia(
            to="+5511999999999",
            media_urls=[
                "https://cdn.example.com/doc.pdf",
                "https://cdn.example.com/audio.mp3",
            ],
            media_types=["application/pdf", "audio/mpeg"],
            media_filenames=["doc.pdf", "audio.mp3"],
        )
        result = gateway.send(msg)

        assert result.succeeded
        # No caption → no sendText call. 2 media files → 2 calls
        assert len(call_log) == 2
        assert "sendFile" in call_log[0]  # application/pdf → document → sendFile
        assert "sendVoice" in call_log[1]  # audio/mpeg → voice → sendVoice

    def test_template_rejected_by_whatsapp_personal(self, whatsapp_provider: WhatsAppPersonalProvider):
        """WhatsApp Personal doesn't support templates — verify clean error."""
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppTemplate(
            to="+5511999999999",
            content_sid="HX123",
            content_variables={"1": "John"},
        )
        result = gateway.send(msg)

        assert not result.succeeded
        assert "template" in (result.error_message or "").lower()


# ── Cross-provider: Phone normalization consistency ──────────────────


class TestPhoneNormalizationE2E:
    """Verify phone normalization is consistent across the full chain."""

    def test_whatsapp_prefix_stripped_for_personal_provider(self, whatsapp_provider: WhatsAppPersonalProvider):
        """WhatsApp Personal adapter expects plain E.164, not whatsapp:+ prefix."""
        mock_client = MagicMock()
        mock_client.post = MagicMock(
            return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value={"payload": {"MessageSid": "ok"}}),
            )
        )
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        gateway.send(msg)

        sent_json = mock_client.post.call_args.kwargs["json"]
        # The provider should normalize the chat ID (strip whatsapp: prefix)
        assert sent_json["chatId"] == "+5511999999999"

    def test_twilio_preserves_whatsapp_prefix(self, twilio_provider: TwilioProvider):
        """Twilio API expects the whatsapp:+ prefix."""
        twilio_provider._client.messages.create = MagicMock(return_value=_twilio_msg())
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        gateway.send(msg)

        call_kwargs = twilio_provider._client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+5511999999999"


# ── Error boundary: Network failures ─────────────────────────────────


class TestNetworkFailureE2E:
    """Verify that network-level failures are caught and returned as DeliveryResult."""

    def test_twilio_connection_error(self, twilio_provider: TwilioProvider):
        twilio_provider._client.messages.create = MagicMock(side_effect=ConnectionError("DNS resolution failed"))
        gateway = MessagingGateway(twilio_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello")
        result = gateway.send(msg)

        assert not result.succeeded
        assert "DNS resolution failed" in (result.error_message or "")

    def test_whatsapp_personal_timeout(self, whatsapp_provider: WhatsAppPersonalProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=httpx.ConnectError("Connection timed out"))
        whatsapp_provider._client = mock_client
        gateway = MessagingGateway(whatsapp_provider)

        msg = WhatsAppText(to="+5511999999999", body="Hello")
        result = gateway.send(msg)

        assert not result.succeeded
        assert "Network error" in (result.error_message or "")


# ── Meta WhatsApp Cloud API: Text end-to-end ─────────────────────────


def _meta_ok(wamid: str = "wamid.meta123") -> MagicMock:
    """Fake Meta API success response."""
    resp = MagicMock()
    resp.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
        "messages": [{"id": wamid}],
    }
    return resp


@pytest.fixture
def meta_provider() -> MetaWhatsAppProvider:
    """MetaWhatsAppProvider for integration tests with mocked httpx client."""
    provider = MetaWhatsAppProvider(MetaWhatsAppConfig(phone_number_id="999888777", access_token="EAAintegration"))
    return provider


class TestMetaWhatsAppTextE2E:
    """Full flow: WhatsAppText → Gateway → MetaWhatsAppProvider → Meta API."""

    def test_text_message_arrives_at_meta_with_correct_payload(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok())
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Hello from integration")
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.meta123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello from integration"


class TestMetaWhatsAppTemplateE2E:
    """Full flow: MetaWhatsAppTemplate → Gateway → MetaWhatsAppProvider → Meta API."""

    def test_template_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.tmpl_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = MetaWhatsAppTemplate(
            to="+5511999999999",
            template_name="order_update",
            language_code="pt_BR",
            components=[{"type": "body", "parameters": [{"type": "text", "text": "John"}]}],
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.tmpl_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_update"
        assert payload["template"]["language"]["code"] == "pt_BR"


class TestMetaWhatsAppInteractiveE2E:
    """Full flow: WhatsAppInteractiveReply → Gateway → MetaWhatsAppProvider → Meta API."""

    def test_interactive_buttons_reach_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.btn_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppInteractiveReply(
            to="whatsapp:+5511999999999",
            body="Choose an option:",
            buttons=[
                {"id": "opt_yes", "title": "Yes"},
                {"id": "opt_no", "title": "No"},
            ],
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.btn_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "button"
        assert payload["interactive"]["body"]["text"] == "Choose an option:"
        buttons = payload["interactive"]["action"]["buttons"]
        assert len(buttons) == 2
        assert buttons[0]["reply"]["id"] == "opt_yes"

    def test_interactive_empty_body_rejected_before_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppInteractiveReply(
            to="+5511999999999",
            body="  ",
            buttons=[{"id": "a", "title": "OK"}],
        )
        result = gateway.send(msg)

        assert not result.succeeded
        assert "No message body" in (result.error_message or "")
        mock_client.post.assert_not_called()

    def test_interactive_rejected_by_twilio_provider(self, twilio_provider: TwilioProvider):
        """Twilio provider does not support interactive messages."""
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppInteractiveReply(
            to="whatsapp:+5511999999999",
            body="Pick one",
            buttons=[{"id": "a", "title": "OK"}],
        )
        result = gateway.send(msg)
        assert not result.succeeded

    def test_interactive_rejected_by_personal_provider(self, whatsapp_provider: WhatsAppPersonalProvider):
        """WhatsApp Personal provider does not support interactive messages."""
        gateway = MessagingGateway(whatsapp_provider)
        msg = WhatsAppInteractiveReply(
            to="+5511999999999",
            body="Pick one",
            buttons=[{"id": "a", "title": "OK"}],
        )
        result = gateway.send(msg)
        assert not result.succeeded


class TestMetaWhatsAppInteractiveTypesE2E:
    """Full flow: new interactive message types → Gateway → MetaWhatsAppProvider → Meta API."""

    def test_list_message_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.list_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppInteractiveList(
            to="whatsapp:+5511999999999",
            body="Pick a dish:",
            button="View options",
            sections=[
                {
                    "title": "Main Courses",
                    "rows": [
                        {"id": "pasta", "title": "Pasta", "description": "Fresh homemade pasta"},
                        {"id": "salad", "title": "Salad"},
                    ],
                }
            ],
            header="Our Menu",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.list_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "list"

    def test_cta_message_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.cta_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppInteractiveCTA(
            to="whatsapp:+5511999999999",
            body="Visit our site",
            display_text="Open Website",
            url="https://example.com",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.cta_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "cta_url"

    def test_product_message_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.prod_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppProduct(
            to="whatsapp:+5511999999999",
            body="Check out this product",
            catalog_id="CAT123",
            product_retailer_id="SKU456",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.prod_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "product"

    def test_product_list_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.prodlist_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppProductList(
            to="whatsapp:+5511999999999",
            body="Browse our products",
            header="Our Catalog",
            catalog_id="CAT789",
            sections=[
                {
                    "title": "Electronics",
                    "product_items": [
                        {"product_retailer_id": "PHONE01"},
                        {"product_retailer_id": "LAPTOP02"},
                    ],
                }
            ],
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.prodlist_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "product_list"

    def test_list_rejected_by_twilio_provider(self, twilio_provider: TwilioProvider):
        """Twilio provider does not support interactive list messages."""
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppInteractiveList(
            to="whatsapp:+5511999999999",
            body="Pick one",
            button="Menu",
            sections=[{"title": "Options", "rows": [{"id": "a", "title": "A"}]}],
        )
        result = gateway.send(msg)
        assert not result.succeeded

    def test_cta_rejected_by_twilio_provider(self, twilio_provider: TwilioProvider):
        """Twilio provider does not support interactive CTA messages."""
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppInteractiveCTA(
            to="whatsapp:+5511999999999",
            body="Visit us",
            display_text="Open",
            url="https://example.com",
        )
        result = gateway.send(msg)
        assert not result.succeeded


class TestMetaWhatsAppNewMessageTypesE2E:
    """Full flow: new message types → Gateway → MetaWhatsAppProvider → Meta API."""

    def test_location_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.loc_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppLocation(
            to="+5511999999999",
            latitude=-23.55,
            longitude=-46.63,
            name="Office",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.loc_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "location"
        assert payload["location"]["latitude"] == -23.55
        assert payload["location"]["longitude"] == -46.63
        assert payload["location"]["name"] == "Office"

    def test_contacts_reach_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.contact_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppContacts(
            to="+5511999999999",
            contacts=[
                {
                    "name": {"formatted_name": "John Doe", "first_name": "John"},
                    "phones": [{"phone": "+5511999999999", "type": "CELL"}],
                }
            ],
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.contact_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "contacts"
        assert len(payload["contacts"]) == 1
        assert payload["contacts"][0]["name"]["formatted_name"] == "John Doe"

    def test_reaction_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.react_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppReaction(
            to="+5511999999999",
            message_id="wamid.xxx",
            emoji="\u2705",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.react_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "reaction"
        assert payload["reaction"]["message_id"] == "wamid.xxx"
        assert payload["reaction"]["emoji"] == "\u2705"

    def test_sticker_reaches_meta_api(self, meta_provider: MetaWhatsAppProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_meta_ok("wamid.sticker_e2e"))
        meta_provider._client = mock_client
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppSticker(
            to="+5511999999999",
            sticker="https://example.com/s.webp",
        )
        result = gateway.send(msg)

        assert result.succeeded
        assert result.external_id == "wamid.sticker_e2e"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "sticker"
        assert payload["sticker"]["link"] == "https://example.com/s.webp"

    def test_location_rejected_by_twilio_provider(self, twilio_provider: TwilioProvider):
        """Twilio provider does not support location messages."""
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppLocation(
            to="whatsapp:+5511999999999",
            latitude=-23.55,
            longitude=-46.63,
        )
        result = gateway.send(msg)
        assert not result.succeeded

    def test_reaction_rejected_by_twilio_provider(self, twilio_provider: TwilioProvider):
        """Twilio provider does not support reaction messages."""
        gateway = MessagingGateway(twilio_provider)
        msg = WhatsAppReaction(
            to="whatsapp:+5511999999999",
            message_id="wamid.xxx",
            emoji="\U0001f44d",
        )
        result = gateway.send(msg)
        assert not result.succeeded


class TestCrossProviderTemplateRejection:
    """Verify providers correctly reject incompatible template types."""

    def test_twilio_rejects_meta_template(self, twilio_provider: TwilioProvider):
        gateway = MessagingGateway(twilio_provider)
        msg = MetaWhatsAppTemplate(
            to="+5511999999999",
            template_name="hello",
            language_code="en_US",
        )
        result = gateway.send(msg)
        assert not result.succeeded
        assert "MetaWhatsAppTemplate" in (result.error_message or "")

    def test_meta_rejects_twilio_template(self, meta_provider: MetaWhatsAppProvider):
        gateway = MessagingGateway(meta_provider)

        msg = WhatsAppTemplate(to="+5511999999999", content_sid="HX123", content_variables={"1": "John"})
        result = gateway.send(msg)

        assert not result.succeeded
        assert "MetaWhatsAppTemplate" in (result.error_message or "")

    def test_whatsapp_personal_rejects_meta_template(self, whatsapp_provider: WhatsAppPersonalProvider):
        gateway = MessagingGateway(whatsapp_provider)
        msg = MetaWhatsAppTemplate(
            to="+5511999999999",
            template_name="hello",
            language_code="en_US",
        )
        result = gateway.send(msg)
        assert not result.succeeded
        assert "template" in (result.error_message or "").lower()


# ── Telegram Bot API: End-to-end ─────────────────────────────────


def _telegram_ok(message_id: int = 42) -> MagicMock:
    """Fake Telegram Bot API success response."""
    resp = MagicMock()
    resp.json.return_value = {"ok": True, "result": {"message_id": message_id}}
    return resp


@pytest.fixture
def telegram_provider() -> TelegramBotProvider:
    """TelegramBotProvider with a mocked httpx client."""
    provider = TelegramBotProvider(TelegramConfig(bot_token="123456789:ABCdefGHI"))
    return provider


class TestTelegramTextE2E:
    """Full flow: TelegramText → TelegramBotProvider → Telegram Bot API."""

    def test_text_message_arrives_at_telegram_api(self, telegram_provider: TelegramBotProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_telegram_ok(100))
        telegram_provider._client = mock_client

        msg = TelegramText(chat_id=12345, body="Hello from integration")
        result = telegram_provider.send(msg)

        assert result.succeeded
        assert result.external_id == "100"
        assert result.status == DeliveryStatus.SENT

        call_args = mock_client.post.call_args
        assert "/sendMessage" in call_args[0][0]
        payload = call_args.kwargs["json"]
        assert payload["chat_id"] == 12345
        assert payload["text"] == "Hello from integration"

    def test_text_with_parse_mode(self, telegram_provider: TelegramBotProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_telegram_ok())
        telegram_provider._client = mock_client

        msg = TelegramText(chat_id=12345, body="<b>Bold</b>", parse_mode="HTML")
        telegram_provider.send(msg)

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["parse_mode"] == "HTML"


class TestTelegramMediaE2E:
    """Full flow: TelegramMedia → TelegramBotProvider → Telegram Bot API."""

    def test_photo_uses_correct_endpoint(self, telegram_provider: TelegramBotProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_telegram_ok())
        telegram_provider._client = mock_client

        msg = TelegramMedia(
            chat_id=12345,
            media_url="https://example.com/photo.jpg",
            media_type="photo",
            caption="A photo",
        )
        result = telegram_provider.send(msg)

        assert result.succeeded
        call_args = mock_client.post.call_args
        assert "/sendPhoto" in call_args[0][0]
        payload = call_args.kwargs["json"]
        assert payload["photo"] == "https://example.com/photo.jpg"
        assert payload["caption"] == "A photo"

    def test_unsupported_media_type_fails(self, telegram_provider: TelegramBotProvider):
        msg = TelegramMedia(
            chat_id=12345,
            media_url="https://example.com/sticker.webp",
            media_type="sticker",
        )
        result = telegram_provider.send(msg)
        assert not result.succeeded
        assert "Unsupported media type" in (result.error_message or "")


class TestTelegramErrorE2E:
    """Telegram API error responses propagate correctly."""

    def test_api_error_returns_failure(self, telegram_provider: TelegramBotProvider):
        mock_client = MagicMock()
        error_resp = MagicMock()
        error_resp.json.return_value = {
            "ok": False,
            "error_code": 403,
            "description": "Forbidden: bot was blocked by the user",
        }
        mock_client.post = MagicMock(return_value=error_resp)
        telegram_provider._client = mock_client

        msg = TelegramText(chat_id=12345, body="Hello")
        result = telegram_provider.send(msg)

        assert not result.succeeded
        assert result.error_code == "403"
        assert "blocked" in (result.error_message or "")

    def test_network_error_returns_failure(self, telegram_provider: TelegramBotProvider):
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=httpx.ConnectError("Connection refused"))
        telegram_provider._client = mock_client

        msg = TelegramText(chat_id=12345, body="Hello")
        result = telegram_provider.send(msg)

        assert not result.succeeded


# ── SMS via Twilio: End-to-end ───────────────────────────────────


@pytest.fixture
def sms_provider() -> TwilioSMSProvider:
    """TwilioSMSProvider with mocked Twilio SDK Client."""
    with patch("messaging.sms.twilio.Client"), patch("messaging.sms.twilio.TwilioHttpClient"):
        config = TwilioSMSConfig(
            account_sid="ACtest",
            auth_token="secret",
            from_number="+14155238886",
            status_callback="https://app.example.com/webhook/sms-status",
        )
        return TwilioSMSProvider(config)


class TestSMSTextE2E:
    """Full flow: SMSMessage → TwilioSMSProvider → Twilio SDK."""

    def test_sms_arrives_at_twilio_with_correct_params(self, sms_provider: TwilioSMSProvider):
        sms_provider._client.messages.create = MagicMock(return_value=_twilio_msg(sid="SM_sms_e2e", status="queued"))

        msg = SMSMessage(to="+5511999999999", body="Your code is 123456")
        result = sms_provider.send(msg)

        assert result.succeeded
        assert result.external_id == "SM_sms_e2e"
        assert result.status == DeliveryStatus.QUEUED

        call_kwargs = sms_provider._client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "+5511999999999"
        assert call_kwargs["from_"] == "+14155238886"
        assert call_kwargs["body"] == "Your code is 123456"
        assert call_kwargs["status_callback"] == "https://app.example.com/webhook/sms-status"

    def test_empty_sms_body_rejected(self, sms_provider: TwilioSMSProvider):
        sms_provider._client.messages.create = MagicMock()

        msg = SMSMessage(to="+5511999999999", body="   ")
        result = sms_provider.send(msg)

        assert not result.succeeded
        sms_provider._client.messages.create.assert_not_called()

    def test_sms_long_body_truncated(self, sms_provider: TwilioSMSProvider):
        sms_provider._client.messages.create = MagicMock(return_value=_twilio_msg())

        msg = SMSMessage(to="+5511999999999", body="x" * 2000)
        sms_provider.send(msg)

        sent_body = sms_provider._client.messages.create.call_args.kwargs["body"]
        assert len(sent_body) == 1600


class TestSMSErrorE2E:
    """SMS error handling end-to-end."""

    def test_twilio_error_returns_failure_with_code(self, sms_provider: TwilioSMSProvider):
        sms_provider._client.messages.create = MagicMock(
            side_effect=TwilioRestException(400, "https://api.twilio.com", msg="Invalid 'To' Phone Number", code=21211)
        )

        msg = SMSMessage(to="+invalid", body="Hi")
        result = sms_provider.send(msg)

        assert not result.succeeded
        assert result.error_code == "21211"

    def test_network_error_returns_failure(self, sms_provider: TwilioSMSProvider):
        sms_provider._client.messages.create = MagicMock(side_effect=ConnectionError("Network unreachable"))

        msg = SMSMessage(to="+5511999999999", body="Hi")
        result = sms_provider.send(msg)

        assert not result.succeeded
        assert "Network unreachable" in (result.error_message or "")
