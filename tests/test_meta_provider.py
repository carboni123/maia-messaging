"""Tests for the Meta WhatsApp Cloud API provider."""

from unittest.mock import MagicMock

import pytest

from messaging import (
    DeliveryStatus,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    WhatsAppMedia,
    WhatsAppTemplate,
    WhatsAppText,
)
from messaging.providers.meta import MetaWhatsAppProvider, _normalize_phone


def _make_provider(config: MetaWhatsAppConfig, mock_response: MagicMock | None = None) -> tuple[MetaWhatsAppProvider, MagicMock]:
    """Create a provider with a mocked httpx client."""
    provider = MetaWhatsAppProvider(config)
    mock_client = MagicMock()
    if mock_response is not None:
        mock_client.post = MagicMock(return_value=mock_response)
    provider._client = mock_client
    return provider, mock_client


def _ok_response(wamid: str = "wamid.HBgN") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
        "messages": [{"id": wamid}],
    }
    return resp


def _error_response(code: int = 100, message: str = "Invalid parameter") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "error": {
            "message": message,
            "type": "OAuthException",
            "code": code,
            "fbtrace_id": "ABC123",
        }
    }
    return resp


class TestMetaWhatsAppProviderInit:
    def test_raises_on_empty_phone_number_id(self):
        with pytest.raises(ValueError, match="phone_number_id is required"):
            MetaWhatsAppProvider(MetaWhatsAppConfig(phone_number_id="", access_token="token"))

    def test_raises_on_empty_access_token(self):
        with pytest.raises(ValueError, match="access_token is required"):
            MetaWhatsAppProvider(MetaWhatsAppConfig(phone_number_id="123", access_token=""))

    def test_constructs_correct_url(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        assert "123456789" in provider._url
        assert "/v21.0/" in provider._url
        assert provider._url.endswith("/messages")


class TestNormalizePhone:
    def test_strips_whatsapp_prefix_and_plus(self):
        assert _normalize_phone("whatsapp:+5511999999999") == "5511999999999"

    def test_strips_plus_only(self):
        assert _normalize_phone("+5511999999999") == "5511999999999"

    def test_plain_number_unchanged(self):
        assert _normalize_phone("5511999999999") == "5511999999999"

    def test_case_insensitive_prefix(self):
        assert _normalize_phone("WhatsApp:+14155238886") == "14155238886"


class TestSendText:
    def test_send_text_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.text123"))

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello!"))

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.text123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello!"

    def test_send_text_strips_whatsapp_prefix(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hi"))

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "5511999999999"

    def test_send_empty_text_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(WhatsAppText(to="+5511999999999", body="   "))
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_text_includes_auth_header(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(WhatsAppText(to="+5511999999999", body="test"))

        headers = mock_client.post.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {meta_whatsapp_config.access_token}"


class TestSendMedia:
    def test_send_photo_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.photo123"))

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/photo.jpg"],
                media_types=["image/jpeg"],
                caption="Look!",
            )
        )

        assert result.succeeded
        assert result.external_id == "wamid.photo123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "image"
        assert payload["image"]["link"] == "https://example.com/photo.jpg"
        assert payload["image"]["caption"] == "Look!"

    def test_send_document_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/report.pdf"],
                media_types=["application/pdf"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "document"
        assert payload["document"]["link"] == "https://example.com/report.pdf"
        assert "caption" not in payload["document"]

    def test_send_video_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/clip.mp4"],
                media_types=["video/mp4"],
                caption="Watch this",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "video"
        assert payload["video"]["link"] == "https://example.com/clip.mp4"

    def test_send_audio_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/voice.ogg"],
                media_types=["audio/ogg"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "audio"

    def test_unknown_mime_defaults_to_document(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/file.xyz"],
                media_types=["application/octet-stream"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "document"

    def test_no_media_urls_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(WhatsAppMedia(to="+5511999999999", media_urls=[]))
        assert not result.succeeded
        assert "No media URLs" in result.error_message

    def test_multiple_media_urls_each_sent(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.last"))

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=[
                    "https://example.com/photo.jpg",
                    "https://example.com/doc.pdf",
                ],
                media_types=["image/jpeg", "application/pdf"],
                caption="See attached",
            )
        )

        assert result.succeeded
        assert mock_client.post.call_count == 2

        # First call: image with caption
        first_payload = mock_client.post.call_args_list[0].kwargs["json"]
        assert first_payload["type"] == "image"
        assert first_payload["image"]["caption"] == "See attached"

        # Second call: document without caption
        second_payload = mock_client.post.call_args_list[1].kwargs["json"]
        assert second_payload["type"] == "document"
        assert "caption" not in second_payload["document"]

    def test_multiple_media_partial_failure_returns_error(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok_response("wamid.first")
            return _error_response(400, "File too large")

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=_side_effect)
        provider._client = mock_client

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/ok.jpg", "https://example.com/big.mp4"],
                media_types=["image/jpeg", "video/mp4"],
            )
        )

        assert not result.succeeded
        assert "File too large" in result.error_message

    def test_audio_caption_not_included(self, meta_whatsapp_config: MetaWhatsAppConfig):
        """Meta Cloud API does not support captions on audio messages."""
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/voice.ogg"],
                media_types=["audio/ogg"],
                caption="This caption should be excluded",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "audio"
        assert "caption" not in payload["audio"]


class TestSendTemplate:
    def test_send_template_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.tmpl123"))

        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "John"},
                    {"type": "text", "text": "Order #42"},
                ],
            }
        ]

        result = provider.send(
            MetaWhatsAppTemplate(
                to="+5511999999999",
                template_name="order_update",
                language_code="en_US",
                components=components,
            )
        )

        assert result.succeeded
        assert result.external_id == "wamid.tmpl123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_update"
        assert payload["template"]["language"]["code"] == "en_US"
        assert payload["template"]["components"] == components

    def test_send_template_without_components(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            MetaWhatsAppTemplate(
                to="+5511999999999",
                template_name="hello_world",
                language_code="en_US",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert "components" not in payload["template"]

    def test_rejects_twilio_whatsapp_template(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppTemplate(to="+5511999999999", content_sid="HX123", content_variables={"1": "John"})
        )
        assert not result.succeeded
        assert "MetaWhatsAppTemplate" in result.error_message


class TestErrorHandling:
    def test_meta_api_error_response(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, _ = _make_provider(
            meta_whatsapp_config,
            _error_response(131030, "Recipient phone number not in allowed list"),
        )

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED
        assert result.error_code == "131030"
        assert "not in allowed list" in result.error_message

    def test_network_error(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=ConnectionError("timeout"))
        provider._client = mock_client

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "timeout" in result.error_message


class TestFetchStatus:
    def test_returns_none(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        assert provider.fetch_status("wamid.xxx") is None


class TestMetaWhatsAppContextManager:
    def test_context_manager_calls_close(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        provider.close = MagicMock()
        with provider:
            pass
        provider.close.assert_called_once()
