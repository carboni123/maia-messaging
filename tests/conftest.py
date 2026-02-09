"""Shared test fixtures for the messaging library."""

import pytest

from messaging import MockProvider, TwilioConfig, WhatsAppPersonalConfig


@pytest.fixture
def twilio_config() -> TwilioConfig:
    return TwilioConfig(
        account_sid="ACtest123",
        auth_token="test_token_456",
        whatsapp_number="whatsapp:+14155238886",
        status_callback="https://example.com/webhook/status",
    )


@pytest.fixture
def whatsapp_personal_config() -> WhatsAppPersonalConfig:
    return WhatsAppPersonalConfig(
        session_public_id="test-session-key",
        api_key="test-api-key",
        adapter_base_url="http://localhost:3001",
    )


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()
