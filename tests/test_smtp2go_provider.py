"""Tests for the SMTP2GO email provider."""

from unittest.mock import MagicMock, patch

from messaging import DeliveryStatus, EmailMessage, Smtp2GoConfig
from messaging.email.smtp2go import SMTP2GO_API_URL, Smtp2GoProvider


class TestSmtp2GoSend:
    def test_send_success(self):
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))

        mock_response = MagicMock(status_code=200, text="OK")
        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_response)))
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))

        mock_response = MagicMock(status_code=500, text="Internal Server Error")
        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_response)))
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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

        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=MagicMock(post=MagicMock(side_effect=ConnectionError("timeout")))
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))

        mock_response = MagicMock(status_code=200, text="OK")
        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="test_key"))

        mock_response = MagicMock(status_code=200, text="OK")
        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
        provider = Smtp2GoProvider(Smtp2GoConfig(api_key="my_secret_key"))

        mock_response = MagicMock(status_code=200, text="OK")
        with patch("messaging.email.smtp2go.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

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
