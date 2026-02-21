"""Benchmark tests for messaging providers.

Measures the overhead of the library's send path with mocked external
boundaries. Useful for catching regressions in hot paths (payload
construction, validation, error mapping) and quantifying the cost of
httpx.Client reuse vs per-request creation.

Run with:
    pytest tests/test_benchmarks.py --benchmark-only -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from messaging import (
    DeliveryResult,
    DeliveryStatus,
    EmailMessage,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    MockProvider,
    SendGridConfig,
    SMSMessage,
    Smtp2GoConfig,
    TelegramConfig,
    TelegramMedia,
    TelegramText,
    TwilioConfig,
    TwilioSMSConfig,
    WhatsAppMedia,
    WhatsAppPersonalConfig,
    WhatsAppTemplate,
    WhatsAppText,
)
from messaging.gateway import MessagingGateway
from messaging.types import GatewayResult


# ── Helpers ────────────────────────────────────────────────────────────


def _twilio_mock_message(sid: str = "SM1234", status: str = "queued") -> MagicMock:
    msg = MagicMock()
    msg.sid = sid
    msg.status = status
    msg.error_code = None
    msg.error_message = None
    return msg


def _httpx_ok_whatsapp() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "messaging_product": "whatsapp",
        "messages": [{"id": "wamid.bench"}],
    }
    return resp


def _httpx_ok_telegram() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
    return resp


def _httpx_ok_smtp2go() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "OK"
    return resp


def _sendgrid_ok_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 202
    resp.body = ""
    return resp


# ── TwilioProvider benchmarks ─────────────────────────────────────────


class TestTwilioProviderBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch("messaging.providers.twilio.Client"), \
             patch("messaging.providers.twilio.TwilioHttpClient"):
            from messaging.providers.twilio import TwilioProvider

            self.provider = TwilioProvider(
                TwilioConfig(
                    account_sid="AC_bench",
                    auth_token="token_bench",
                    whatsapp_number="whatsapp:+14155238886",
                )
            )
            self.provider._client.messages.create.return_value = _twilio_mock_message()
            yield

    def test_send_text(self, benchmark):
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Benchmark text")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_media(self, benchmark):
        msg = WhatsAppMedia(
            to="whatsapp:+5511999999999",
            media_urls=["https://example.com/photo.jpg"],
            caption="Benchmark media",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_template(self, benchmark):
        msg = WhatsAppTemplate(
            to="whatsapp:+5511999999999",
            content_sid="HX_bench",
            content_variables={"1": "World"},
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_text_long_body_truncation(self, benchmark):
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="A" * 3000)
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── TwilioProvider async benchmarks ───────────────────────────────────


class TestTwilioAsyncBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch("messaging.providers.twilio.Client"), \
             patch("messaging.providers.twilio.TwilioHttpClient"):
            from messaging.providers.twilio import TwilioProvider

            self.provider = TwilioProvider(
                TwilioConfig(
                    account_sid="AC_bench",
                    auth_token="token_bench",
                    whatsapp_number="whatsapp:+14155238886",
                )
            )
            self.provider._client.messages.create.return_value = _twilio_mock_message()
            yield

    def test_send_async_text(self, benchmark):
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Async bench")

        def run():
            return asyncio.run(self.provider.send_async(msg))

        result = benchmark(run)
        assert result.succeeded


# ── MetaWhatsAppProvider benchmarks ───────────────────────────────────


class TestMetaProviderBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from messaging.providers.meta import MetaWhatsAppProvider

        self.provider = MetaWhatsAppProvider(
            MetaWhatsAppConfig(phone_number_id="123456", access_token="EAA_bench")
        )
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_httpx_ok_whatsapp())
        self.provider._client = mock_client
        yield

    def test_send_text(self, benchmark):
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Meta bench")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_media_single(self, benchmark):
        msg = WhatsAppMedia(
            to="+5511999999999",
            media_urls=["https://example.com/photo.jpg"],
            media_types=["image/jpeg"],
            caption="Bench",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_media_multiple(self, benchmark):
        """Benchmark sequential multi-media sends (reusing a single httpx.Client)."""
        msg = WhatsAppMedia(
            to="+5511999999999",
            media_urls=[
                "https://example.com/a.jpg",
                "https://example.com/b.pdf",
                "https://example.com/c.mp4",
            ],
            media_types=["image/jpeg", "application/pdf", "video/mp4"],
            caption="Multi-media bench",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_template(self, benchmark):
        msg = MetaWhatsAppTemplate(
            to="+5511999999999",
            template_name="order_update",
            language_code="en_US",
            components=[
                {"type": "body", "parameters": [{"type": "text", "text": "John"}]},
            ],
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── WhatsAppPersonalProvider benchmarks ───────────────────────────────


class TestWhatsAppPersonalBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.patcher = patch("messaging.providers.whatsapp_personal.requests.post")
        mock_post = self.patcher.start()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.json.return_value = {
            "payload": {"MessageSid": "SM_bench_personal"}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from messaging.providers.whatsapp_personal import WhatsAppPersonalProvider

        self.provider = WhatsAppPersonalProvider(
            WhatsAppPersonalConfig(
                session_public_id="bench-session",
                api_key="bench-key",
                adapter_base_url="http://localhost:3001",
            )
        )
        yield
        self.patcher.stop()

    def test_send_text(self, benchmark):
        msg = WhatsAppText(to="+5511999999999", body="Personal bench")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_media_with_caption(self, benchmark):
        msg = WhatsAppMedia(
            to="+5511999999999",
            media_urls=["https://example.com/photo.jpg"],
            media_types=["image/jpeg"],
            caption="Personal media bench",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── TelegramBotProvider benchmarks ────────────────────────────────────


class TestTelegramBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from messaging.telegram.bot_api import TelegramBotProvider

        self.provider = TelegramBotProvider(
            TelegramConfig(bot_token="123:ABCbench")
        )
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_httpx_ok_telegram())
        self.provider._client = mock_client
        yield

    def test_send_text(self, benchmark):
        msg = TelegramText(chat_id=12345, body="Telegram bench")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_text_with_parse_mode(self, benchmark):
        msg = TelegramText(chat_id=12345, body="<b>Bold</b>", parse_mode="HTML")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_photo(self, benchmark):
        msg = TelegramMedia(
            chat_id=12345,
            media_url="https://example.com/photo.jpg",
            media_type="photo",
            caption="Bench photo",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_document(self, benchmark):
        msg = TelegramMedia(
            chat_id=12345,
            media_url="https://example.com/doc.pdf",
            media_type="document",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── TwilioSMSProvider benchmarks ─────────────────────────────────────


class TestTwilioSMSBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch("messaging.sms.twilio.Client"), \
             patch("messaging.sms.twilio.TwilioHttpClient"):
            from messaging.sms.twilio import TwilioSMSProvider

            self.provider = TwilioSMSProvider(
                TwilioSMSConfig(
                    account_sid="AC_bench",
                    auth_token="token_bench",
                    from_number="+14155238886",
                )
            )
            self.provider._client.messages.create.return_value = _twilio_mock_message(
                sid="SM_sms_bench"
            )
            yield

    def test_send_sms(self, benchmark):
        msg = SMSMessage(to="+5511999999999", body="SMS bench")
        result = benchmark(self.provider.send, msg)
        assert result.succeeded

    def test_send_sms_long_body(self, benchmark):
        msg = SMSMessage(to="+5511999999999", body="B" * 2000)
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── SendGridProvider benchmarks ───────────────────────────────────────


class TestSendGridBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch("messaging.email.sendgrid.SendGridAPIClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.send.return_value = _sendgrid_ok_response()
            mock_cls.return_value = mock_client
            from messaging.email.sendgrid import SendGridProvider

            self.provider = SendGridProvider(SendGridConfig(api_key="SG.bench"))
            yield

    def test_send_email(self, benchmark):
        msg = EmailMessage(
            to="user@example.com",
            subject="Bench subject",
            html_content="<p>Bench body</p>",
            from_email="noreply@example.com",
            from_name="Bench",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── Smtp2GoProvider benchmarks ────────────────────────────────────────


class TestSmtp2GoBenchmarks:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from messaging.email.smtp2go import Smtp2GoProvider

        self.provider = Smtp2GoProvider(Smtp2GoConfig(api_key="bench_key"))
        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=_httpx_ok_smtp2go())
        self.provider._client = mock_client
        yield

    def test_send_email(self, benchmark):
        msg = EmailMessage(
            to="user@example.com",
            subject="Bench subject",
            html_content="<p>Bench body</p>",
            from_email="noreply@example.com",
        )
        result = benchmark(self.provider.send, msg)
        assert result.succeeded


# ── MockProvider benchmarks ───────────────────────────────────────────


class TestMockProviderBenchmarks:
    def test_send_text(self, benchmark):
        provider = MockProvider()
        msg = WhatsAppText(to="+5511999999999", body="Mock bench")
        result = benchmark(provider.send, msg)
        assert result.succeeded

    def test_send_1000_messages(self, benchmark):
        """Benchmark MockProvider accumulation overhead."""
        provider = MockProvider()
        msgs = [
            WhatsAppText(to=f"+551199999{i:04d}", body=f"Msg {i}")
            for i in range(1000)
        ]

        def send_batch():
            for m in msgs:
                provider.send(m)
            count = len(provider.sent)
            provider.reset()
            return count

        count = benchmark(send_batch)
        assert count == 1000


# ── MessagingGateway benchmarks ───────────────────────────────────────


class TestGatewayBenchmarks:
    def test_send_no_fallback(self, benchmark):
        provider = MockProvider()
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Gateway bench")
        result = benchmark(gateway.send, msg)
        assert result.succeeded

    def test_send_with_fallback_enabled_no_error(self, benchmark):
        provider = MockProvider()
        gateway = MessagingGateway(provider)
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Gateway fallback bench")

        def send_with_fallback():
            return gateway.send(msg, phone_fallback=True)

        result = benchmark(send_with_fallback)
        assert result.succeeded

    def test_send_with_fallback_triggered(self, benchmark):
        """Benchmark the fallback retry path (two sends per call)."""
        call_count = 0

        class FallbackProvider:
            def send(self, message):
                nonlocal call_count
                call_count += 1
                if call_count % 2 == 1:
                    return DeliveryResult.fail("invalid number format")
                return DeliveryResult.ok(external_id="FB_bench")

            def fetch_status(self, external_id):
                return None

        gateway = MessagingGateway(FallbackProvider())
        msg = WhatsAppText(to="whatsapp:+5511999999999", body="Fallback bench")

        def send_with_fallback():
            return gateway.send(msg, phone_fallback=True)

        result = benchmark(send_with_fallback)
        assert result.succeeded


# ── DeliveryResult construction benchmarks ────────────────────────────


class TestDeliveryResultBenchmarks:
    def test_ok_construction(self, benchmark):
        result = benchmark(DeliveryResult.ok, status=DeliveryStatus.SENT, external_id="SM123")
        assert result.succeeded

    def test_fail_construction(self, benchmark):
        result = benchmark(
            DeliveryResult.fail, "Something went wrong", error_code="500"
        )
        assert not result.succeeded

    def test_status_precedence(self, benchmark):
        statuses = list(DeliveryStatus)

        def check_all():
            return [s.precedence for s in statuses]

        precedences = benchmark(check_all)
        assert len(precedences) == len(statuses)


# ── Dataclass creation benchmarks ─────────────────────────────────────


class TestMessageCreationBenchmarks:
    def test_whatsapp_text_creation(self, benchmark):
        def create():
            return WhatsAppText(to="+5511999999999", body="Hello")

        msg = benchmark(create)
        assert msg.to == "+5511999999999"

    def test_whatsapp_media_creation(self, benchmark):
        def create():
            return WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://a.com/1.jpg", "https://a.com/2.pdf"],
                media_types=["image/jpeg", "application/pdf"],
                media_filenames=["photo.jpg", "doc.pdf"],
                caption="Files",
            )

        msg = benchmark(create)
        assert len(msg.media_urls) == 2

    def test_email_message_creation(self, benchmark):
        def create():
            return EmailMessage(
                to="user@example.com",
                subject="Subject",
                html_content="<p>Body</p>",
                from_email="noreply@example.com",
                from_name="System",
            )

        msg = benchmark(create)
        assert msg.to == "user@example.com"

    def test_sms_message_creation(self, benchmark):
        def create():
            return SMSMessage(to="+5511999999999", body="SMS")

        msg = benchmark(create)
        assert msg.body == "SMS"

    def test_telegram_text_creation(self, benchmark):
        def create():
            return TelegramText(chat_id=12345, body="TG", parse_mode="HTML")

        msg = benchmark(create)
        assert msg.chat_id == 12345
