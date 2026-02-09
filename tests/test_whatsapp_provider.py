"""Tests for the WhatsApp Personal provider."""

from unittest.mock import MagicMock, patch

from messaging import WhatsAppMedia, WhatsAppPersonalConfig, WhatsAppTemplate, WhatsAppText
from messaging.providers.whatsapp_personal import WhatsAppPersonalProvider


class TestWhatsAppSendText:
    def test_send_text_success(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "payload": {
                "Sid": "msg_123",
                "MessageSid": "msg_123",
                "AccountSid": "ACC123",
                "MessagingServiceSid": "MSS123",
                "Direction": "outbound",
                "Status": "sent",
                "DateCreated": "2024-01-01",
                "DateUpdated": "2024-01-01",
                "NumSegments": "1",
                "NumMedia": "0",
                "Price": "0",
                "PriceUnit": "USD",
                "ApiVersion": "v1",
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert result.succeeded
        assert result.external_id == "msg_123"

    def test_send_empty_text_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        result = provider.send(WhatsAppText(to="+5511999999999", body="  "))
        assert not result.succeeded
        assert "empty" in result.error_message.lower()

    def test_send_long_text_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        result = provider.send(WhatsAppText(to="+5511999999999", body="x" * 2000))
        assert not result.succeeded
        assert "exceeds" in result.error_message.lower()

    def test_send_text_missing_message_id_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"payload": {"Status": "sent"}}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "missing message id" in (result.error_message or "").lower()

    def test_send_text_adapter_error_payload_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"error": "quota exceeded"}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "quota exceeded" in (result.error_message or "").lower()

    def test_send_text_accepts_formatted_plus_number(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"payload": {"MessageSid": "msg_123"}}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response) as mock_post:
            result = provider.send(WhatsAppText(to="+55 (11) 99999-9999", body="Hello"))

        assert result.succeeded
        sent_payload = mock_post.call_args.kwargs["json"]
        assert sent_payload["chatId"] == "+5511999999999"


class TestWhatsAppSendMedia:
    def test_send_media_success(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"id": {"_serialized": "media_456"}}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/file.pdf"],
                media_types=["application/pdf"],
                media_filenames=["report.pdf"],
            )
            result = provider.send(msg)

        assert result.succeeded
        assert result.external_id == "media_456"

    def test_send_media_no_urls_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        result = provider.send(WhatsAppMedia(to="+5511999999999"))
        assert not result.succeeded

    def test_send_media_missing_message_id_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"payload": {"Status": "sent"}}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/file.pdf"],
            )
            result = provider.send(msg)

        assert not result.succeeded
        assert "missing message id" in (result.error_message or "").lower()

    def test_send_media_error_payload_fails(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"error": "adapter rejected media"}
        mock_response.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/file.pdf"],
            )
            result = provider.send(msg)

        assert not result.succeeded
        assert "adapter rejected media" in (result.error_message or "").lower()


class TestWhatsAppTemplate:
    def test_template_not_supported(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        msg = WhatsAppTemplate(to="+5511999999999", content_sid="HX123")
        result = provider.send(msg)
        assert not result.succeeded
        assert "does not support template" in result.error_message.lower()


class TestWhatsAppFetchStatus:
    def test_returns_none(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        assert provider.fetch_status("any_id") is None


class TestWhatsAppNetworkErrors:
    def test_connection_error(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        import requests

        with patch(
            "messaging.providers.whatsapp_personal.requests.post",
            side_effect=requests.ConnectionError("Connection refused"),
        ):
            result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "Network error" in result.error_message

    def test_http_error_includes_status_and_body(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        import requests

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "invalid api key"
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "401 Client Error",
            response=mock_response,
        )

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=mock_response):
            result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "401" in (result.error_message or "")
        assert "invalid api key" in (result.error_message or "")
