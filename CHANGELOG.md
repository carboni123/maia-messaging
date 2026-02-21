# Changelog

All notable changes to `maia-messaging` will be documented in this file.

## [0.4.0] - 2026-02-21

### Added

- **Async support (`send_async`)** on all providers: Twilio WhatsApp, Meta WhatsApp, WhatsApp Personal, Telegram, SMTP2GO, SendGrid, Twilio SMS, and the Gateway. Uses `asyncio.to_thread()` to offload blocking I/O without starving the event loop.
- **Async context managers (`async with`)** on all httpx-based providers (Meta, WhatsApp Personal, Telegram, SMTP2GO). Providers now support both `with provider:` and `async with provider:`.
- **Sync context managers (`with`)** on all httpx-based providers for deterministic resource cleanup.
- **`send_async` declared in Protocol definitions** (`MessagingProvider`, `EmailProvider`, `SMSProvider`, `TelegramProvider`) so mypy enforces implementation on all providers.
- **Thread safety** for concurrent `send_async` calls. Each httpx-based provider holds a `threading.Lock` that serializes access to the shared `httpx.Client`, preventing data corruption when multiple `to_thread` calls run in parallel.
- **Connection pooling** via `httpx.Client` (created once in `__init__`, reused across calls) on Meta, WhatsApp Personal, Telegram, and SMTP2GO providers. Replaces per-request connection creation.
- **Request timeouts** on all providers: httpx-based providers use `httpx.Client(timeout=...)`, Twilio-based providers use `TwilioHttpClient(timeout=...)`.
- **Benchmark test suite** (`tests/test_benchmarks.py`) with 32 `pytest-benchmark` tests covering all provider send paths and a 1000-message throughput test.
- **`pytest-asyncio`** added to test dependencies with `asyncio_mode = "auto"`.

### Changed

- **Migrated WhatsApp Personal provider from `requests` to `httpx`**. Exception mapping: `requests.HTTPError` -> `httpx.HTTPStatusError`, `requests.RequestException` -> `httpx.RequestError`, `requests.ConnectionError` -> `httpx.ConnectError`.
- **`MockProvider.send_async`** no longer uses `asyncio.to_thread()` since mock has no blocking I/O; calls `self.send()` directly.
- All test files updated to use direct `provider._client = mock_client` injection instead of `patch("...requests.post")` context managers.

### Removed

- **`requests` direct dependency** removed from `pyproject.toml`. The library now depends only on `twilio`, `sendgrid`, and `httpx`. (Note: `twilio` SDK still pulls `requests` transitively.)
- **`types-requests`** removed from test dependencies.

## [0.3.0] - 2026-02-20

### Added

- **Meta WhatsApp Cloud API provider** (`MetaWhatsAppProvider`) supporting text, media (image/video/audio/document), and template messages via Meta's Graph API.
- **Telegram Bot API provider** (`TelegramBotProvider`) supporting text, photo, document, and video messages.
- `MetaWhatsAppTemplate` message type with language code and components for Meta's template format.
- `TelegramText` and `TelegramMedia` message types with `chat_id` (int | str) addressing.
- `TelegramConfig` and `MetaWhatsAppConfig` configuration dataclasses.
- `TelegramProvider` protocol in `telegram/base.py`.
