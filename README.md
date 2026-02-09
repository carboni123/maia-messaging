# maia-messaging

WhatsApp delivery library for the Meu Assistente IA platform.

Owns the delivery layer: everything from "I have a resolved message and provider config" to "here's what happened." The consuming app keeps orchestration (credential lookup, quota, logging).

## Install

```bash
pip install maia-messaging@git+https://github.com/carboni123/maia-messaging.git
```

## Usage

### Send a text message via Twilio

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
  mock.py              # MockProvider for testing
  pricing.py           # WhatsApp template cost calculator
  phone/
    normalize.py       # normalize_phone, format_whatsapp_number, phones_match
    brazil.py          # Brazil-specific 8↔9 digit rules
  providers/
    base.py            # MessagingProvider protocol
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
| `TwilioConfig` | Twilio credentials + whatsapp number |
| `WhatsAppPersonalConfig` | WWjs adapter credentials |

### Provider protocol

Any provider implements two methods:

```python
class MessagingProvider(Protocol):
    def send(self, message: Message) -> DeliveryResult: ...
    def fetch_status(self, external_id: str) -> DeliveryResult | None: ...
```

### Status precedence

`DeliveryStatus` has a `.precedence` property for ordering:

```
QUEUED(1) → SENT(4) → DELIVERED(5) → READ(6)
FAILED(-1), UNDELIVERED(-2)
```

```python
if new_status.precedence > current_status.precedence:
    # Status progressed forward
```

## Boundary: what stays in the app

| Concern | Why it stays in the app |
|---------|------------------------|
| Integration resolution | Queries DB for Twilio credentials |
| CommunicationLog creation | Tied to app's DB schema |
| Quota enforcement | Queries billing tables |
| Session lifecycle | Business rules + DB models |
| Template CRUD | Content API management, not delivery |
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

139 tests total (116 unit + 23 integration), all run in <0.3s with zero external dependencies.

- `test_types.py` — DeliveryResult, DeliveryStatus.precedence, message dataclasses
- `test_gateway.py` — Phone fallback logic, status fetch
- `test_twilio_provider.py` — Twilio SDK mocked, dispatch + response mapping
- `test_whatsapp_provider.py` — HTTP adapter mocked, dispatch + response mapping
- `test_phone_normalize.py` — Brazil normalization, format_whatsapp_number, phones_match
- `test_pricing.py` — Template cost calculation
- `test_mock.py` — MockProvider recording and failure simulation
- `test_integration.py` — Full Gateway → Provider → (mocked external) → DeliveryResult flows
