# CLAUDE.md

## What is this

`maia-messaging` is a standalone Python library that owns multi-channel message delivery. It was extracted from the `meuassistenteia-app` backend to create a single source of truth for messaging that can be validated independently.

Package name: `maia-messaging`
Import name: `messaging`

## Key constraints

- **Zero app dependencies.** This library must never import from the consuming app (no `app.models`, no `app.settings`, no SQLAlchemy, no FastAPI, no Celery). If you need something from the app, it belongs in the app's adapter layer, not here.
- **No database.** All state is passed in via function arguments and returned via dataclasses.
- **Tests run in isolation.** `pytest tests/` must pass with only `twilio`, `requests`, `sendgrid`, and `httpx` installed. Mock external boundaries (Twilio SDK, HTTP calls, SendGrid API), never real services.

## Development commands

```bash
pip install -e ".[test]"
pytest tests/ -v
ruff check messaging/ tests/ --fix
mypy messaging/
```

## Architecture

The library has eight layers:

1. **Types** (`types.py`) — Frozen dataclasses for messages, results, and configs. These are the public contract.
2. **WhatsApp Providers** (`providers/`) — `TwilioProvider`, `MetaWhatsAppProvider`, and `WhatsAppPersonalProvider` implement the `MessagingProvider` protocol. Each wraps one external service.
3. **Email Providers** (`email/`) — `SendGridProvider` and `Smtp2GoProvider` implement the `EmailProvider` protocol.
4. **SMS Providers** (`sms/`) — `TwilioSMSProvider` implements the `SMSProvider` protocol.
5. **Telegram Providers** (`telegram/`) — `TelegramBotProvider` implements the `TelegramProvider` protocol. Sends text, photo, document, and video messages via the Telegram Bot API.
6. **Content API** (`content_api.py`) — `TwilioContentAPI` for WhatsApp template CRUD via the Twilio Content API.
7. **Gateway** (`gateway.py`) — Optional orchestration layer that adds cross-cutting concerns (phone fallback for Brazilian numbers).
8. **Phone** (`phone/`) — Pure functions for phone number normalization. Brazil-specific logic in `brazil.py`, generic in `normalize.py`.

Plus `pricing.py` (WhatsApp template costs) and `mock.py` (test provider).

## Conventions

- All message types are frozen dataclasses with `slots=True`
- WhatsApp providers return `DeliveryResult`, never raise for delivery failures
- Email providers return `DeliveryResult`, never raise for delivery failures
- SMS providers return `DeliveryResult`, never raise for delivery failures
- Telegram providers return `DeliveryResult`, never raise for delivery failures
- All providers expose `send_async()` via `asyncio.to_thread(self.send, message)` for safe async usage
- Providers using `httpx` create the client once in `__init__` and expose a `close()` method for cleanup
- Twilio SDK providers use `TwilioHttpClient(timeout=10.0)` to prevent indefinite hangs
- `TwilioContentAPI` methods raise `TwilioContentAPIError` on failure
- `DeliveryResult.ok()` and `DeliveryResult.fail()` are the preferred constructors
- Phone functions accept `str | None` and return `str | None` (null-safe)
- Tests are organized by module: `test_twilio_provider.py` tests `providers/twilio.py`
- Integration tests (`test_integration.py`) wire real library components, only mock the external boundary
- Benchmark tests (`test_benchmarks.py`) measure provider overhead with `pytest-benchmark`

## Adding a new WhatsApp provider

1. Create `providers/your_provider.py` implementing `MessagingProvider`
2. Add a config dataclass to `types.py`
3. Export from `providers/__init__.py` and `__init__.py`
4. Add unit tests in `tests/test_your_provider.py`
5. Add integration tests in `tests/test_integration.py`

## Adding a new email provider

1. Create `email/your_provider.py` implementing `EmailProvider`
2. Add a config dataclass to `types.py`
3. Export from `email/__init__.py` and `__init__.py`
4. Add unit tests in `tests/test_your_provider.py`

## Adding a new SMS provider

1. Create `sms/your_provider.py` implementing `SMSProvider`
2. Add a config dataclass to `types.py`
3. Export from `sms/__init__.py` and `__init__.py`
4. Add unit tests in `tests/test_your_provider.py`

## Adding a new Telegram provider

1. Create `telegram/your_provider.py` implementing `TelegramProvider`
2. Add a config dataclass to `types.py`
3. Export from `telegram/__init__.py` and `__init__.py`
4. Add unit tests in `tests/test_your_provider.py`
