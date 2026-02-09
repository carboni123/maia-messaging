"""Tests for the SendGrid email provider."""

from unittest.mock import MagicMock, patch

from messaging import DeliveryStatus, EmailMessage, SendGridConfig
from messaging.email.sendgrid import SendGridProvider


def _make_provider() -> SendGridProvider:
    """Create a SendGridProvider with a mocked client."""
    with patch("messaging.email.sendgrid.SendGridAPIClient"):
        return SendGridProvider(SendGridConfig(api_key="SG.test_key"))


class TestSendGridSend:
    def test_send_success(self):
        provider = _make_provider()
        mock_response = MagicMock(status_code=202, body=b"")
        provider._client.send = MagicMock(return_value=mock_response)

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
                from_name="Test App",
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        provider._client.send.assert_called_once()

    def test_send_failure_status(self):
        provider = _make_provider()
        mock_response = MagicMock(status_code=400, body=b"Bad Request")
        provider._client.send = MagicMock(return_value=mock_response)

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )

        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED
        assert "400" in result.error_code

    def test_send_exception(self):
        provider = _make_provider()
        provider._client.send = MagicMock(side_effect=ConnectionError("network error"))

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
            )
        )

        assert not result.succeeded
        assert "network error" in result.error_message

    def test_send_constructs_mail_correctly(self):
        provider = _make_provider()
        mock_response = MagicMock(status_code=200, body=b"")
        provider._client.send = MagicMock(return_value=mock_response)

        provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Welcome",
                html_content="<h1>Hi</h1>",
                from_email="noreply@test.com",
                from_name="My App",
            )
        )

        call_args = provider._client.send.call_args
        mail = call_args[0][0]
        assert mail.subject.get() == "Welcome"

    def test_send_without_from_name(self):
        provider = _make_provider()
        mock_response = MagicMock(status_code=200, body=b"")
        provider._client.send = MagicMock(return_value=mock_response)

        result = provider.send(
            EmailMessage(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                from_email="noreply@example.com",
                from_name="",
            )
        )

        assert result.succeeded
