"""Tests for the Telegram Bot API provider."""

from unittest.mock import MagicMock

import pytest

from messaging import DeliveryStatus, TelegramConfig, TelegramMedia, TelegramText
from messaging.telegram.bot_api import TelegramBotProvider


def _make_provider(config: TelegramConfig, mock_response: MagicMock | None = None) -> tuple[TelegramBotProvider, MagicMock]:
    """Create a provider with a mocked httpx client."""
    provider = TelegramBotProvider(config)
    mock_client = MagicMock()
    if mock_response is not None:
        mock_client.post = MagicMock(return_value=mock_response)
    provider._client = mock_client
    return provider, mock_client


def _ok_response(message_id: int = 42) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"ok": True, "result": {"message_id": message_id}}
    return resp


def _error_response(error_code: int = 400, description: str = "Bad Request") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"ok": False, "error_code": error_code, "description": description}
    return resp


class TestTelegramBotProviderInit:
    def test_raises_on_empty_token(self):
        with pytest.raises(ValueError, match="bot_token is required"):
            TelegramBotProvider(TelegramConfig(bot_token=""))


class TestSendText:
    def test_send_text_success(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response(message_id=99))

        result = provider.send(TelegramText(chat_id=12345, body="Hello!"))

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "99"

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["chat_id"] == 12345
        assert payload["text"] == "Hello!"
        assert "parse_mode" not in payload

    def test_send_text_with_parse_mode(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response())

        result = provider.send(TelegramText(chat_id="12345", body="<b>Bold</b>", parse_mode="HTML"))

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["parse_mode"] == "HTML"

    def test_send_text_with_string_chat_id(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response())

        result = provider.send(TelegramText(chat_id="@mychannel", body="Channel post"))

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["chat_id"] == "@mychannel"

    def test_send_text_uses_correct_url(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response())

        provider.send(TelegramText(chat_id=1, body="test"))

        url = mock_client.post.call_args[0][0]
        assert url.endswith("/sendMessage")
        assert telegram_config.bot_token in url


class TestSendMedia:
    def test_send_photo_success(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response(message_id=55))

        result = provider.send(
            TelegramMedia(
                chat_id=12345,
                media_url="https://example.com/photo.jpg",
                media_type="photo",
                caption="Look at this!",
            )
        )

        assert result.succeeded
        assert result.external_id == "55"

        url = mock_client.post.call_args[0][0]
        assert url.endswith("/sendPhoto")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["chat_id"] == 12345
        assert payload["photo"] == "https://example.com/photo.jpg"
        assert payload["caption"] == "Look at this!"

    def test_send_document_success(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response())

        result = provider.send(
            TelegramMedia(
                chat_id=12345,
                media_url="https://example.com/file.pdf",
                media_type="document",
            )
        )

        assert result.succeeded
        url = mock_client.post.call_args[0][0]
        assert url.endswith("/sendDocument")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["document"] == "https://example.com/file.pdf"
        assert "caption" not in payload

    def test_send_video_success(self, telegram_config: TelegramConfig):
        provider, mock_client = _make_provider(telegram_config, _ok_response())

        result = provider.send(
            TelegramMedia(
                chat_id=12345,
                media_url="https://example.com/video.mp4",
                media_type="video",
                caption="Watch this",
                parse_mode="HTML",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["video"] == "https://example.com/video.mp4"
        assert payload["caption"] == "Watch this"
        assert payload["parse_mode"] == "HTML"

    def test_unsupported_media_type(self, telegram_config: TelegramConfig):
        provider = TelegramBotProvider(telegram_config)

        result = provider.send(
            TelegramMedia(
                chat_id=12345,
                media_url="https://example.com/file.xyz",
                media_type="sticker",
            )
        )

        assert not result.succeeded
        assert result.error_code == "unsupported_media_type"
        assert "sticker" in result.error_message


class TestErrorHandling:
    def test_api_error_response(self, telegram_config: TelegramConfig):
        provider, _ = _make_provider(
            telegram_config,
            _error_response(403, "Forbidden: bot was blocked by the user"),
        )

        result = provider.send(TelegramText(chat_id=12345, body="Hello"))

        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED
        assert result.error_code == "403"
        assert "blocked by the user" in result.error_message

    def test_network_error(self, telegram_config: TelegramConfig):
        provider = TelegramBotProvider(telegram_config)
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=ConnectionError("timeout"))
        provider._client = mock_client

        result = provider.send(TelegramText(chat_id=12345, body="Hello"))

        assert not result.succeeded
        assert "timeout" in result.error_message


class TestTelegramBotContextManager:
    def test_context_manager_calls_close(self, telegram_config: TelegramConfig):
        provider = TelegramBotProvider(telegram_config)
        provider.close = MagicMock()
        with provider:
            pass
        provider.close.assert_called_once()
