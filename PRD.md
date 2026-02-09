# PRD: maia-messaging

## Purpose

`maia-messaging` is a multi-channel, multi-provider library for **sending messages**. It handles everything from "I have a message and provider credentials" to "here's what happened." Nothing else.

The library does not process inbound messages, persist logs, enforce quotas, resolve credentials, or make routing decisions. Those responsibilities belong to the consuming application.

## Problem

The consuming app (Meu Assistente IA) evolved multiple independent messaging paths:

- Campaign sends went through one code path with Twilio
- Chat session replies went through a different path with a provider abstraction
- Agent tools and PDF reports called Twilio directly, bypassing both

Each path had its own result types, error handling, and provider wiring. Adding a new provider or channel meant touching every path. There was no way to unit-test delivery logic without a database.

## Solution

A standalone library with:

1. **One interface per channel** — `MessagingProvider` for WhatsApp, `EmailProvider` for email
2. **One result type** — `DeliveryResult` for all providers and channels
3. **Provider implementations** — Plug in credentials, call `.send()`, get a result
4. **Zero app dependencies** — No database, no Redis, no Celery, no app settings

## Scope

### What the library owns

| Concern | Description |
|---------|-------------|
| **Message delivery** | Send a message through a provider and return a `DeliveryResult` |
| **Provider implementations** | Twilio (WhatsApp), WhatsApp Personal (WWjs adapter), SendGrid (email), SMTP2GO (email) |
| **Message types** | `WhatsAppText`, `WhatsAppMedia`, `WhatsAppTemplate`, `EmailMessage` |
| **Unified result** | `DeliveryResult` with status, external_id, error_code, error_message |
| **Status polling** | `fetch_status()` to check delivery state of a previously sent message |
| **Phone normalization** | Format numbers for delivery: E.164, `whatsapp:` prefix, Brazil 8/9-digit handling |
| **Phone fallback** | `MessagingGateway` retries with alternate phone format on invalid-number errors |
| **Template management** | `TwilioContentAPI` for creating, listing, and checking approval status of WhatsApp templates |
| **Pricing** | Calculate per-message cost by WhatsApp template category |
| **Test support** | `MockProvider` that records sent messages and supports configurable failure rates |

### What the library does NOT own

| Concern | Why it stays in the app |
|---------|------------------------|
| Inbound message processing | Webhook handlers depend on app routing, DB models, event bus |
| Message logging / CommunicationLog | Database model tied to app schema |
| Credential resolution | Requires DB queries (which Twilio account for which tenant) |
| Quota and billing enforcement | Requires billing tables and tenant configuration |
| Send gate policy | Business rules tied to tenant config and campaign state |
| Session lifecycle | WhatsApp 24h windows, QR codes, connection status — integration management, not delivery |
| Routing decisions | Choosing which provider or channel for a given recipient |
| Event bus / real-time notifications | App-level infrastructure |
| Celery task orchestration | App-level scheduling |

## Architecture

### Core contract

Every provider follows the same pattern:

```
Config  +  Message  -->  Provider.send()  -->  DeliveryResult
```

- **Config**: Immutable dataclass with provider credentials (`TwilioConfig`, `SendGridConfig`, etc.)
- **Message**: Immutable dataclass describing what to send (`WhatsAppText`, `EmailMessage`, etc.)
- **DeliveryResult**: Immutable dataclass with `status`, `external_id`, `error_code`, `error_message`, `succeeded`

### Channels and providers

| Channel | Provider | Config | Message types |
|---------|----------|--------|---------------|
| WhatsApp | `TwilioProvider` | `TwilioConfig` | `WhatsAppText`, `WhatsAppMedia`, `WhatsAppTemplate` |
| WhatsApp | `WhatsAppPersonalProvider` | `WhatsAppPersonalConfig` | `WhatsAppText`, `WhatsAppMedia` |
| Email | `SendGridProvider` | `SendGridConfig` | `EmailMessage` |
| Email | `Smtp2GoProvider` | `Smtp2GoConfig` | `EmailMessage` |
| Test | `MockProvider` | None | Any `Message` type |

### Protocols

- **`MessagingProvider`** — `send(Message) -> DeliveryResult` + `fetch_status(external_id) -> DeliveryResult | None`
- **`EmailProvider`** — `send(EmailMessage) -> DeliveryResult`

### Gateway layer

`MessagingGateway` wraps a `MessagingProvider` and adds:

- **Phone fallback**: On invalid-number errors, retries with the alternate Brazilian phone format (9-digit to 8-digit). Returns `GatewayResult` with `used_fallback_number` if fallback succeeded.

### Template management

`TwilioContentAPI` is a separate class (not a provider) that manages WhatsApp message templates via the Twilio Content API:

- `create_template()` — Create or replace a content template, optionally submit for WhatsApp approval
- `get_template_status()` — Check approval status of a template
- `list_templates()` — List all templates with approval metadata
- `create_quick_reply()` — Create a session-scoped quick-reply content template

### Utilities

- **Phone normalization** — `normalize_phone()`, `format_whatsapp_number()`, `denormalize_phone_for_whatsapp()`, `phones_match()`
- **Pricing** — `calculate_template_cost(category)` returns the cost per template category (marketing, utility, authentication)

## Design principles

1. **Stateless**: Providers hold only config. No connection pooling, no caching, no side effects beyond the API call.
2. **Immutable types**: All configs, messages, and results are frozen dataclasses. No mutation after creation.
3. **Errors as values**: Provider failures return `DeliveryResult(status=FAILED)` instead of raising exceptions. Only configuration errors (bad credentials, missing fields) raise.
4. **Zero app imports**: The library depends only on provider SDKs (`twilio`, `sendgrid`, `httpx`, `requests`). Never on the consuming app.
5. **Testable in isolation**: All 164 tests run without DB, Redis, Celery, or network. `MockProvider` enables consumer-side testing without mocking internals.

## Extension points

Adding a new provider requires:

1. A config dataclass in `types.py`
2. A provider class implementing `MessagingProvider` or `EmailProvider`
3. Tests in `tests/`
4. Export in `__init__.py`

Adding a new channel (e.g., SMS) requires:

1. A new message dataclass (e.g., `SMSMessage`)
2. Adding it to the `Message` union type
3. A provider that accepts the new message type
4. Handling in the gateway if fallback logic applies
