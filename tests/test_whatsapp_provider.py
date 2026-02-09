"""Tests for the WhatsApp Personal provider."""

from unittest.mock import MagicMock, patch

from messaging import DeliveryStatus, WhatsAppMedia, WhatsAppPersonalConfig, WhatsAppTemplate, WhatsAppText
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


class TestWhatsAppMediaMimeRouting:
    """Verify that different MIME types route to the correct adapter endpoint."""

    def _make_success_response(self, msg_id: str = "media_ok") -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"id": {"_serialized": msg_id}}
        resp.raise_for_status = MagicMock()
        return resp

    def test_image_routes_to_send_image(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=self._make_success_response()) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/photo.jpg"],
                media_types=["image/jpeg"],
            )
            result = provider.send(msg)

        assert result.succeeded
        call_url = mock_post.call_args.args[0]
        assert call_url.endswith("/api/sendImage")

    def test_video_routes_to_send_video(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=self._make_success_response()) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/clip.mp4"],
                media_types=["video/mp4"],
            )
            result = provider.send(msg)

        assert result.succeeded
        call_url = mock_post.call_args.args[0]
        assert call_url.endswith("/api/sendVideo")

    def test_audio_routes_to_send_voice(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=self._make_success_response()) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/voice.ogg"],
                media_types=["audio/ogg"],
            )
            result = provider.send(msg)

        assert result.succeeded
        call_url = mock_post.call_args.args[0]
        assert call_url.endswith("/api/sendVoice")

    def test_document_routes_to_send_file(self, whatsapp_personal_config: WhatsAppPersonalConfig):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=self._make_success_response()) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/report.pdf"],
                media_types=["application/pdf"],
                media_filenames=["report.pdf"],
            )
            result = provider.send(msg)

        assert result.succeeded
        call_url = mock_post.call_args.args[0]
        assert call_url.endswith("/api/sendFile")


class TestWhatsAppMediaCaptionFlow:
    """Caption is sent as separate text message first, then media without caption."""

    def _make_text_response(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"payload": {"MessageSid": "text_001"}}
        resp.raise_for_status = MagicMock()
        return resp

    def _make_media_response(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"id": {"_serialized": "media_001"}}
        resp.raise_for_status = MagicMock()
        return resp

    def test_caption_sent_as_text_then_media_without_caption(
        self, whatsapp_personal_config: WhatsAppPersonalConfig,
    ):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        responses = [self._make_text_response(), self._make_media_response()]

        with patch("messaging.providers.whatsapp_personal.requests.post", side_effect=responses) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/photo.jpg"],
                media_types=["image/jpeg"],
                caption="Look at this!",
            )
            result = provider.send(msg)

        assert result.succeeded
        # First call: sendText with caption
        first_call = mock_post.call_args_list[0]
        assert first_call.args[0].endswith("/api/sendText")
        assert first_call.kwargs["json"]["text"] == "Look at this!"
        # Second call: sendImage without caption
        second_call = mock_post.call_args_list[1]
        assert second_call.args[0].endswith("/api/sendImage")
        assert "caption" not in second_call.kwargs["json"]


class TestWhatsAppMultiFileMedia:
    """Multi-file sends loop through each media URL."""

    def _make_response(self, msg_id: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"id": {"_serialized": msg_id}}
        resp.raise_for_status = MagicMock()
        return resp

    def test_multiple_files_sent_individually(
        self, whatsapp_personal_config: WhatsAppPersonalConfig,
    ):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)
        responses = [self._make_response("id_1"), self._make_response("id_2")]

        with patch("messaging.providers.whatsapp_personal.requests.post", side_effect=responses) as mock_post:
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=[
                    "https://example.com/photo.jpg",
                    "https://example.com/doc.pdf",
                ],
                media_types=["image/jpeg", "application/pdf"],
                media_filenames=["photo.jpg", "doc.pdf"],
            )
            result = provider.send(msg)

        assert result.succeeded
        assert mock_post.call_count == 2
        # First goes to sendImage, second to sendFile
        assert mock_post.call_args_list[0].args[0].endswith("/api/sendImage")
        assert mock_post.call_args_list[1].args[0].endswith("/api/sendFile")
        # external_id is from first successful send
        assert result.external_id == "id_1"

    def test_partial_failure_returns_failed_status_with_id(
        self, whatsapp_personal_config: WhatsAppPersonalConfig,
    ):
        """When some files succeed and others fail, status=FAILED but external_id is set."""
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        success_resp = self._make_response("id_ok")
        error_resp = MagicMock()
        error_resp.status_code = 200
        error_resp.headers = {"Content-Type": "application/json"}
        error_resp.json.return_value = {"error": "file too large"}
        error_resp.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", side_effect=[success_resp, error_resp]):
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=[
                    "https://example.com/photo.jpg",
                    "https://example.com/huge.zip",
                ],
                media_types=["image/jpeg", "application/zip"],
            )
            result = provider.send(msg)

        # Has errors but also has a successful send
        assert result.status == DeliveryStatus.FAILED
        assert result.external_id == "id_ok"
        assert "file too large" in (result.error_message or "")

    def test_all_files_fail(
        self, whatsapp_personal_config: WhatsAppPersonalConfig,
    ):
        provider = WhatsAppPersonalProvider(whatsapp_personal_config)

        error_resp = MagicMock()
        error_resp.status_code = 200
        error_resp.headers = {"Content-Type": "application/json"}
        error_resp.json.return_value = {"error": "upload failed"}
        error_resp.raise_for_status = MagicMock()

        with patch("messaging.providers.whatsapp_personal.requests.post", return_value=error_resp):
            msg = WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/f1.pdf", "https://example.com/f2.pdf"],
                media_types=["application/pdf", "application/pdf"],
            )
            result = provider.send(msg)

        assert not result.succeeded
        assert result.external_id is None


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
