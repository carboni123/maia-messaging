"""Tests for the SMTP2GO email provider."""

from unittest.mock import MagicMock

from messaging import DeliveryStatus, EmailMessage, Smtp2GoConfig
from messaging.email.smtp2go import SMTP2GO_API_URL, Smtp2GoProvider


def _make_provider(api_key: str = "test_key", mock_response: MagicMock | None = None) -> tuple[Smtp2GoProvider, MagicMock]:
    """Create a provider with a mocked httpx client."""
    provider = Smtp2GoProvider(Smtp2GoConfig(api_key=api_key))
    mock_client = MagicMock()
    if mock_response is not None:
        mock_client.post = MagicMock(return_value=mock_response)
    provider._client = mock_client
    return provider, mock_client


class TestSmtp2GoSend:
    def test_send_success(self):
        provider, _ = _make_provider(mock_response=MagicMock(status_code=200, text="OK"))

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
                from_name="My App",
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT

    def test_send_failure_status(self):
        provider, _ = _make_provider(mock_response=MagicMock(status_code=500, text="Internal Server Error"))

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )

        assert not result.succeeded
        assert "500" in result.error_code

    def test_send_exception(self):
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=ConnectionError("timeout"))
        provider._client = mock_client

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )

        assert not result.succeeded
        assert "timeout" in result.error_message

    def test_send_formats_sender_with_name(self):
        provider, mock_client = _make_provider(mock_response=MagicMock(status_code=200, text="OK"))

        provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
                from_name="My App",
            )
        )

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["sender"] == "My App <noreply@example.com>"
        assert payload["to"] == ["user@example.com"]
        assert payload["subject"] == "Test"
        assert payload["html_body"] == "<p>Hello</p>"

    def test_send_formats_sender_without_name(self):
        provider, mock_client = _make_provider(mock_response=MagicMock(status_code=200, text="OK"))

        provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
                from_name="",
            )
        )

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["sender"] == "noreply@example.com"

    def test_send_uses_correct_api_url_and_headers(self):
        provider, mock_client = _make_provider(
            api_key="my_secret_key",
            mock_response=MagicMock(status_code=200, text="OK"),
        )

        provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )

        call_args = mock_client.post.call_args
        assert call_args[0][0] == SMTP2GO_API_URL
        assert call_args.kwargs["headers"]["X-Smtp2go-Api-Key"] == "my_secret_key"


class TestSmtp2GoContextManager:
    def test_context_manager_calls_close(self):
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))
        provider.close = MagicMock()
        with provider:
            pass
        provider.close.assert_called_once()

    async def test_async_context_manager_calls_close(self):
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))
        provider.close = MagicMock()
        async with provider:
            pass
        provider.close.assert_called_once()


class TestSmtp2GoSendAsync:
    async def test_send_async_returns_result(self):
        provider, _ = _make_provider(mock_response=MagicMock(status_code=200, text="OK"))
        result = await provider.send_async(
            EmailMessage(
                to="user@example.com",
                subject="Async Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )
        assert result.succeeded
