# CLAUDE.md

## What is this

`maia-messaging` is a standalone Python library that owns WhatsApp message delivery. It was extracted from the `meuassistenteia-app` backend to create a single source of truth for messaging that can be validated independently.

Package name: `maia-messaging`
Import name: `messaging`

## Key constraints

- **Zero app dependencies.** This library must never import from the consuming app (no `app.models`, no `app.settings`, no SQLAlchemy, no FastAPI, no Celery). If you need something from the app, it belongs in the app's adapter layer, not here.
- **No database.** All state is passed in via function arguments and returned via dataclasses.
- **Tests run in isolation.** `pytest tests/` must pass with only `twilio` and `requests` installed. Mock external boundaries (Twilio SDK, HTTP calls), never real services.

## Development commands

```bash
pip install -e ".[test]"
pytest tests/ -v
ruff check messaging/ tests/ --fix
mypy messaging/
```

## Architecture

The library has four layers:

1. **Types** (`types.py`) — Frozen dataclasses for messages, results, and configs. These are the public contract.
2. **Providers** (`providers/`) — `TwilioProvider` and `WhatsAppPersonalProvider` implement the `MessagingProvider` protocol. Each wraps one external service.
3. **Gateway** (`gateway.py`) — Optional orchestration layer that adds cross-cutting concerns (phone fallback for Brazilian numbers).
4. **Phone** (`phone/`) — Pure functions for phone number normalization. Brazil-specific logic in `brazil.py`, generic in `normalize.py`.

Plus `pricing.py` (WhatsApp template costs) and `mock.py` (test provider).

## Conventions

- All message types are frozen dataclasses with `slots=True`
- Providers return `DeliveryResult`, never raise for delivery failures
- `DeliveryResult.ok()` and `DeliveryResult.fail()` are the preferred constructors
- Phone functions accept `str | None` and return `str | None` (null-safe)
- Tests are organized by module: `test_twilio_provider.py` tests `providers/twilio.py`
- Integration tests (`test_integration.py`) wire real library components, only mock the external boundary

## Adding a new provider

1. Create `providers/your_provider.py` implementing `MessagingProvider`
2. Add a config dataclass to `types.py`
3. Export from `providers/__init__.py` and `__init__.py`
4. Add unit tests in `tests/test_your_provider.py`
5. Add integration tests in `tests/test_integration.py`
