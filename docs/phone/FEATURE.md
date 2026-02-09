# Phone Normalization - Feature

**State**: `ACTIVE`
**Version**: 1.0
**Created**: 2026-01-16

---

## Overview

Centralized phone number normalization utilities with country-specific handling. Primary focus is Brazilian mobile number normalization to handle the 8-to-9 digit transition completed in 2016.

## Problem Solved

Brazilian mobile numbers transitioned from 8 to 9 digits (adding a leading `9`) in 2016. Legacy data and some external systems still use the old 8-digit format, causing customer de-duplication failures.

**Example**: Customer "Thiago Carboni Reiter" with phone `+555198644323` (old format) was not matched with incoming "Thiago carboni" with phone `+5551998644323` (new format), creating a duplicate.

## Solution

1. **Normalize on Storage**: All phone numbers normalized to 9-digit format before storing
2. **Normalize on Comparison**: `phones_match()` normalizes both numbers before comparing
3. **WhatsApp Fallback**: If 9-digit fails, try 8-digit and persist working format

## Directory Structure

```
backend/app/core/phone/
├── __init__.py      # Module exports
├── brazil.py        # Brazil-specific normalization
├── normalize.py     # Generic normalization entry points
└── FEATURE.md       # This file
```

## Public API

```python
from app.core.phone import (
    normalize_phone,           # Normalize any phone to E.164
    normalize_whatsapp_id,     # Normalize WhatsApp ID
    phones_match,              # Compare two phones after normalization
    denormalize_phone_for_whatsapp,  # Get 8-digit fallback format
)
```

## Usage Examples

```python
# Normalize before storage
customer.phone_number = normalize_phone("+555198644323")  # → "+5551998644323"

# Compare potentially different formats
if phones_match(existing_phone, incoming_phone):
    # Same customer - update instead of create
    pass

# WhatsApp fallback when 9-digit fails
fallback = denormalize_phone_for_whatsapp("+5551998644323")  # → "+555198644323"
```

## Integration Points

| Component | Usage |
|-----------|-------|
| CRM Ingestion Routes | Customer lookup and creation |
| CRM Core Service | Customer create/update |
| CRM Ingestion Helpers | `find_or_create_customer()` |
| Chat Session Messaging | WhatsApp delivery fallback |

## Related Documentation

- [CONTRACTS.md](./CONTRACTS.md) - API contracts and data types
- [Tests](../../../../tests/core/test_phone_normalization.py) - Unit tests
