# maia-messaging

Multi-channel messaging library for the Meu Assistente IA platform.

Owns the delivery layer: everything from "I have a resolved message and provider config" to "here's what happened." The consuming app keeps orchestration (credential lookup, quota, logging).

Supports WhatsApp (Twilio + Personal), Email (SendGrid + SMTP2GO), and Twilio Content API template management.

## Install

```bash
pip install maia-messaging@git+https://github.com/carboni123/maia-messaging.git
```

## Usage

### Send a WhatsApp text message via Twilio

```python
from messaging import TwilioProvider, TwilioConfig, WhatsAppText

provider = TwilioProvider(TwilioConfig(
    account_sid="AC...",
    auth_token="...",
    whatsapp_number="whatsapp:+14155238886",
))
result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello!"))
if result.succeeded:
    print(result.external_id)  # Twilio SID
```

### Send media

```python
from messaging import WhatsAppMedia

result = provider.send(WhatsAppMedia(
    to="whatsapp:+5511999999999",
    media_urls=["https://example.com/report.pdf"],
    caption="Here is your report.",
))
```

### Send a template (Twilio Content API)

```python
from messaging import WhatsAppTemplate

result = provider.send(WhatsAppTemplate(
    to="whatsapp:+5511999999999",
    content_sid="HX...",
    content_variables={"1": "John", "2": "Order #123"},
))
```

### Send email via SendGrid

```python
from messaging import SendGridProvider, SendGridConfig, EmailMessage

provider = SendGridProvider(SendGridConfig(api_key="SG..."))
result = provider.send(EmailMessage(
    to="user@example.com",
    subject="Welcome",
    html_content="<h1>Hello!</h1>",
    from_email="noreply@example.com",
    from_name="My App",
))
if result.succeeded:
    print("Email sent!")
```

### Send email via SMTP2GO

```python
from messaging import Smtp2GoProvider, Smtp2GoConfig, EmailMessage

provider = Smtp2GoProvider(Smtp2GoConfig(api_key="api-..."))
result = provider.send(EmailMessage(
    to="user@example.com",
    subject="Hello",
    html_content="<p>Hi there</p>",
    from_email="noreply@example.com",
))
```

### Manage WhatsApp templates (Twilio Content API)

```python
from messaging import TwilioContentAPI, TwilioConfig

api = TwilioContentAPI(TwilioConfig(
    account_sid="AC...",
    auth_token="...",
    whatsapp_number="whatsapp:+14155238886",
))

# Create a template
template = api.create_template(
    friendly_name="order_update",
    language="en",
    types={"twilio_text": {"body": "Your order {{1}} is {{2}}."}},
    whatsapp_template_name="order_update",  # Submit for WhatsApp approval
    category="UTILITY",
)

# Check approval status
status = api.get_template_status(template_sid="HX...")

# List all templates
templates = api.list_templates()

# Create a quick-reply (session messages, no approval needed)
qr = api.create_quick_reply(
    body="Would you like to continue?",
    buttons=[
        {"id": "yes", "title": "Yes"},
        {"id": "no", "title": "No"},
    ],
)
```

### Phone fallback via Gateway

Brazilian phone numbers have a 9-digit / 8-digit ambiguity. The `MessagingGateway` handles automatic retry:

```python
from messaging import MessagingGateway

gateway = MessagingGateway(provider)
result = gateway.send(message, phone_fallback=True)
# If 9-digit fails with "invalid number", retries with 8-digit
if result.used_fallback_number:
    print(f"Delivered using: {result.used_fallback_number}")
```

### WhatsApp Personal (via WWjs adapter)

```python
from messaging import WhatsAppPersonalProvider, WhatsAppPersonalConfig, WhatsAppText

provider = WhatsAppPersonalProvider(WhatsAppPersonalConfig(
    session_public_id="sess_abc",
    api_key="key_123",
    adapter_base_url="http://localhost:3001",
))
result = provider.send(WhatsAppText(to="+5511999999999", body="Hello!"))
```

### Phone normalization

```python
from messaging import normalize_phone, format_whatsapp_number, phones_match

normalize_phone("+555198644323")           # "+5551998644323" (adds 9th digit)
format_whatsapp_number("+5511999999999")   # "whatsapp:+5511999999999"
phones_match("+555198644323", "+5551998644323")  # True
```

### Testing with MockProvider

```python
from messaging import MockProvider, WhatsAppText

provider = MockProvider()
result = provider.send(WhatsAppText(to="+5511...", body="test"))
assert result.succeeded
assert len(provider.sent) == 1

# Simulate failures
provider = MockProvider(failure_rate=0.5)  # 50% random failures
provider = MockProvider(fixed_result=DeliveryResult.fail("quota exceeded"))
```

### Template pricing

```python
from messaging import calculate_template_cost

calculate_template_cost("MARKETING")       # Decimal("0.0600")
calculate_template_cost("UTILITY")         # Decimal("0.0200")
calculate_template_cost("AUTHENTICATION")  # Decimal("0.0150")
calculate_template_cost(None)              # Decimal("0.0200") (default)
```

## Architecture

```
messaging/
  __init__.py          # Public API (all exports)
  types.py             # DeliveryResult, DeliveryStatus, Message types, configs
  gateway.py           # MessagingGateway — phone fallback logic
  content_api.py       # TwilioContentAPI — template CRUD via Twilio Content API
  mock.py              # MockProvider for testing
  pricing.py           # WhatsApp template cost calculator
  email/
    base.py            # EmailProvider protocol
    sendgrid.py        # SendGridProvider
    smtp2go.py         # Smtp2GoProvider
  phone/
    normalize.py       # normalize_phone, format_whatsapp_number, phones_match
    brazil.py          # Brazil-specific 8↔9 digit rules
  providers/
    base.py            # MessagingProvider protocol (WhatsApp)
    twilio.py          # TwilioProvider + empty_messaging_response_xml
    whatsapp_personal.py  # WhatsAppPersonalProvider (WWjs adapter)
```

### Key types

| Type | Purpose |
|------|---------|
| `DeliveryResult` | Result of a send attempt: status, external_id, error info |
| `DeliveryStatus` | Enum: QUEUED, SENT, DELIVERED, READ, FAILED, UNDELIVERED |
| `GatewayResult` | Wraps DeliveryResult with `used_fallback_number` |
| `WhatsAppText` | Text message (`to`, `body`) |
| `WhatsAppMedia` | Media message (`to`, `media_urls`, `caption`) |
| `WhatsAppTemplate` | Template message (`to`, `content_sid`, `content_variables`) |
| `EmailMessage` | Email message (`to`, `subject`, `html_content`, `from_email`, `from_name`) |
| `TwilioConfig` | Twilio credentials + whatsapp number |
| `WhatsAppPersonalConfig` | WWjs adapter credentials |
| `SendGridConfig` | SendGrid API key |
| `Smtp2GoConfig` | SMTP2GO API key |

### Provider protocols

WhatsApp providers implement:

```python
class MessagingProvider(Protocol):
    def send(self, message: Message) -> DeliveryResult: ...
    def fetch_status(self, external_id: str) -> DeliveryResult | None: ...
```

Email providers implement:

```python
class EmailProvider(Protocol):
    def send(self, message: EmailMessage) -> DeliveryResult: ...
```

### Template management

`TwilioContentAPI` wraps the Twilio Content API for managing WhatsApp message templates:

```python
class TwilioContentAPI:
    def create_template(self, ...) -> dict[str, Any]: ...
    def get_template_status(self, *, template_sid: str) -> dict[str, Any]: ...
    def list_templates(self, *, page_size: int = 50) -> list[dict[str, Any]]: ...
    def create_quick_reply(self, ...) -> dict[str, Any]: ...
```

Raises `TwilioContentAPIError` on API failures (with `.status` and `.code` attributes).

### Status precedence

`DeliveryStatus` has a `.precedence` property for ordering:

```
QUEUED(1) -> SENT(4) -> DELIVERED(5) -> READ(6)
FAILED(-1), UNDELIVERED(-2)
```

```python
if new_status.precedence > current_status.precedence:
    # Status progressed forward
```

## Boundary: what stays in the app

| Concern | Why it stays in the app |
|---------|------------------------|
| Integration resolution | Queries DB for Twilio/email credentials |
| CommunicationLog creation | Tied to app's DB schema |
| Quota enforcement | Queries billing tables |
| Session lifecycle | Business rules + DB models |
| Status webhook processing | DB updates, event bus, signature validation |
| Event bus / WebSocket | App-level real-time infrastructure |

## Development

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run tests (no DB, no Redis, no external services)
pytest tests/ -v

# Lint
ruff check messaging/ tests/
```

## Tests

164 tests total, all run in <0.3s with zero external dependencies.

- `test_types.py` — DeliveryResult, DeliveryStatus.precedence, message dataclasses
- `test_gateway.py` — Phone fallback logic, status fetch
- `test_twilio_provider.py` — Twilio SDK mocked, dispatch + response mapping
- `test_whatsapp_provider.py` — HTTP adapter mocked, dispatch + response mapping
- `test_sendgrid_provider.py` — SendGrid SDK mocked, email dispatch
- `test_smtp2go_provider.py` — httpx mocked, SMTP2GO API dispatch
- `test_content_api.py` — Template CRUD, quick-reply, error handling
- `test_phone_normalize.py` — Brazil normalization, format_whatsapp_number, phones_match
- `test_pricing.py` — Template cost calculation
- `test_mock.py` — MockProvider recording and failure simulation
- `test_integration.py` — Full Gateway -> Provider -> (mocked external) -> DeliveryResult flows
