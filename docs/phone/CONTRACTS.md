# Phone Normalization - Contracts

**Version**: 1.0
**Last Updated**: 2026-01-16

---

## 1. Function Signatures

### 1.1 normalize_phone

```python
def normalize_phone(phone: str | None, default_country: str = "BR") -> str | None:
    """Normalize a phone number to E.164 format.

    Args:
        phone: Raw phone number (any format)
        default_country: Default country code if not detected (default: "BR")

    Returns:
        Normalized E.164 format (e.g., "+5511999999999") or None if invalid
    """
```

### 1.2 normalize_whatsapp_id

```python
def normalize_whatsapp_id(whatsapp_id: str | None, default_country: str = "BR") -> str | None:
    """Normalize a WhatsApp ID to E.164 format.

    Args:
        whatsapp_id: Raw WhatsApp ID (e.g., "whatsapp:+5511999999999" or "+5511999999999")
        default_country: Default country code if not detected (default: "BR")

    Returns:
        Normalized WhatsApp ID or None if invalid
    """
```

### 1.3 phones_match

```python
def phones_match(phone1: str | None, phone2: str | None, country: str = "BR") -> bool:
    """Check if two phone numbers match after normalization.

    Args:
        phone1: First phone number
        phone2: Second phone number
        country: Country code for normalization rules

    Returns:
        True if both normalize to the same number
    """
```

### 1.4 denormalize_phone_for_whatsapp

```python
def denormalize_phone_for_whatsapp(phone: str | None, country: str = "BR") -> str | None:
    """Convert a normalized phone back to alternate format for WhatsApp fallback.

    Used when the normalized format fails - try the alternate format.
    For Brazil, this converts 9-digit mobile back to 8-digit.

    Args:
        phone: Normalized phone number
        country: Country code

    Returns:
        Alternate format or original if no alternate exists
    """
```

---

## 2. Brazil-Specific Functions

### 2.1 normalize_brazil_phone

```python
def normalize_brazil_phone(phone: str | None) -> str | None:
    """Normalize a Brazilian phone number to E.164 format with 9th digit.

    Handles:
    - Adding country code (+55) if missing
    - Adding 9th digit to mobile numbers that don't have it
    - Stripping formatting characters
    - WhatsApp prefix (whatsapp:+55...)

    Args:
        phone: Raw phone number string

    Returns:
        Normalized phone in format +5511999999999 or None if invalid
    """
```

### 2.2 denormalize_brazil_phone

```python
def denormalize_brazil_phone(phone: str | None) -> str | None:
    """Convert a 9-digit mobile number back to 8-digit format.

    This is used as a fallback when the normalized 9-digit format
    doesn't work (some WhatsApp accounts registered with old format).

    Args:
        phone: Normalized phone number (+5511999999999)

    Returns:
        8-digit format (+551199999999) or original if not applicable
    """
```

### 2.3 phones_match_brazil

```python
def phones_match_brazil(phone1: str | None, phone2: str | None) -> bool:
    """Check if two phone numbers match after Brazilian normalization.

    Handles the 9th digit discrepancy by normalizing both before comparison.
    """
```

---

## 3. Constants

### 3.1 Brazil Constants

```python
BRAZIL_COUNTRY_CODE = "55"

# All 2-digit area codes (DDD) from 11-99
BRAZIL_AREA_CODES = {str(i) for i in range(11, 100)}

# First digits that indicate mobile numbers
BRAZIL_MOBILE_PREFIXES = "9876"
```

---

## 4. Normalization Rules

### 4.1 Brazilian Phone Normalization

| Input Format | Output Format | Notes |
|--------------|---------------|-------|
| `+555198644323` | `+5551998644323` | Old 8-digit → 9-digit |
| `+5551998644323` | `+5551998644323` | Already normalized |
| `5198644323` | `+5551998644323` | Without country code |
| `(51) 9864-4323` | `+5551998644323` | With formatting |
| `+555133224455` | `+555133224455` | Landline unchanged |
| `whatsapp:+555198644323` | `whatsapp:+5551998644323` | WhatsApp prefix preserved |
| `12345` | `None` | Invalid (too short) |

### 4.2 Mobile Detection

A number is considered mobile if:
1. It has 8 digits (local part, excluding DDD)
2. First digit is 9, 8, 7, or 6

Mobile numbers get the 9th digit added. Landlines (starting with 2-5) remain unchanged.

---

## 5. Error Handling

All functions return `None` for invalid inputs rather than raising exceptions:
- `None` input
- Empty string
- Whitespace-only string
- Too few digits (< 10 for Brazil)
- Too many digits (> 11 for Brazil local)

---

## 6. Exports

```python
# From app.core.phone
__all__ = [
    # Main API
    "normalize_phone",
    "normalize_whatsapp_id",
    "phones_match",
    "denormalize_phone_for_whatsapp",
    # Brazil-specific (for direct use if needed)
    "normalize_brazil_phone",
    "denormalize_brazil_phone",
    "phones_match_brazil",
]
```
