"""Phone normalization utilities with country-specific handling.

This module provides a centralized way to normalize phone numbers before
storage and comparison, handling country-specific rules like Brazil's
8 to 9 digit mobile transition.
"""

from __future__ import annotations

import re

from .brazil import denormalize_brazil_phone, normalize_brazil_phone, phones_match_brazil


def normalize_phone(phone: str | None, default_country: str = "BR") -> str | None:
    """Normalize a phone number to E.164 format.

    Applies country-specific normalization rules. Currently supports:
    - Brazil (BR): Adds 9th digit to mobile numbers

    Args:
        phone: Raw phone number
        default_country: Default country code if not detected (default: BR)

    Returns:
        Normalized E.164 format or None if invalid
    """
    if not phone:
        return None

    phone = phone.strip()
    if not phone:
        return None

    whatsapp_prefix, candidate = _split_whatsapp_prefix(phone)
    candidate = candidate.strip()
    if not candidate:
        return None

    # Extract digits to detect country
    digits = re.sub(r"\D", "", candidate)
    if not digits:
        return None

    # Explicit +55 numbers are always treated as Brazilian.
    if digits.startswith("55"):
        return normalize_brazil_phone(f"{whatsapp_prefix}{candidate}")

    # International numbers should not be rewritten to Brazil just because
    # default_country is BR.
    if candidate.startswith("+"):
        return f"{whatsapp_prefix}+{digits}"

    # Local numbers (without country code) follow the default country.
    if default_country.upper() == "BR":
        return normalize_brazil_phone(f"{whatsapp_prefix}{candidate}")

    # Generic normalization for other countries
    return f"{whatsapp_prefix}+{digits}"


def normalize_whatsapp_id(whatsapp_id: str | None, default_country: str = "BR") -> str | None:
    """Normalize a WhatsApp ID to E.164 format.

    WhatsApp IDs are phone numbers, potentially prefixed with "whatsapp:".
    This function normalizes the underlying phone number.
    """
    if not whatsapp_id:
        return None

    whatsapp_id = whatsapp_id.strip()
    if not whatsapp_id:
        return None

    has_whatsapp_prefix = whatsapp_id.lower().startswith("whatsapp:")
    raw_phone = whatsapp_id[9:] if has_whatsapp_prefix else whatsapp_id

    normalized = normalize_phone(raw_phone, default_country)
    if not normalized:
        return None

    if has_whatsapp_prefix and not normalized.lower().startswith("whatsapp:"):
        return f"whatsapp:{normalized}"

    return normalized


def denormalize_phone_for_whatsapp(phone: str | None, country: str = "BR") -> str | None:
    """Convert a normalized phone back to alternate format for WhatsApp fallback.

    Used when the normalized format fails - try the alternate format.
    For Brazil, this converts 9-digit mobile back to 8-digit.
    """
    if not phone:
        return None

    if country == "BR":
        return denormalize_brazil_phone(phone)

    return phone


def format_whatsapp_number(number: str | None) -> str | None:
    """Normalize a phone number to the ``whatsapp:+E.164`` format.

    Args:
        number: The raw phone number which may include punctuation or a ``whatsapp:`` prefix.

    Returns:
        The number formatted as ``whatsapp:+E.164`` or ``None`` if input is empty.
    """
    if not number:
        return None

    number = number.strip()
    if number.lower().startswith("whatsapp:"):
        number = number[9:]

    digits = re.sub(r"\D", "", number)
    if not digits:
        return None

    if len(digits) == 10:  # Assume US numbers without country code
        digits = "1" + digits

    return f"whatsapp:+{digits}"


def phones_match(phone1: str | None, phone2: str | None, country: str = "BR") -> bool:
    """Check if two phone numbers match after normalization.

    Handles country-specific normalization rules before comparison.
    """
    if country == "BR":
        return phones_match_brazil(phone1, phone2)

    # Generic comparison
    norm1 = normalize_phone(phone1, country)
    norm2 = normalize_phone(phone2, country)
    return norm1 == norm2 if norm1 and norm2 else False


def _split_whatsapp_prefix(value: str) -> tuple[str, str]:
    """Split a WhatsApp prefix while preserving canonical lowercase form."""
    if value.lower().startswith("whatsapp:"):
        return "whatsapp:", value[9:]
    return "", value
