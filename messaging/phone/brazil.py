"""Brazilian phone number normalization utilities.

Handles the 8 to 9 digit mobile number migration that Brazil completed in 2016.
All mobile numbers now have 9 digits (starting with 9), but legacy data and some
external systems may still have the old 8-digit format.
"""

from __future__ import annotations

import re

BRAZIL_COUNTRY_CODE = "55"

# Brazilian area codes (DDD) - all 2-digit codes from 11-99
BRAZIL_AREA_CODES = {str(i) for i in range(11, 100)}

# First digits that indicate mobile numbers (historically 9, 8, 7, 6)
BRAZIL_MOBILE_PREFIXES = "9876"


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

    Examples:
        >>> normalize_brazil_phone("+555198644323")
        '+5551998644323'
        >>> normalize_brazil_phone("+5551998644323")
        '+5551998644323'
        >>> normalize_brazil_phone("5198644323")
        '+5551998644323'
        >>> normalize_brazil_phone("whatsapp:+555198644323")
        'whatsapp:+5551998644323'
    """
    if not phone:
        return None

    phone = phone.strip()

    # Handle WhatsApp prefix
    whatsapp_prefix = ""
    if phone.lower().startswith("whatsapp:"):
        whatsapp_prefix = "whatsapp:"
        phone = phone[9:]  # Remove "whatsapp:" prefix

    # Extract digits only
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None

    # Remove country code if present
    if digits.startswith("55") and len(digits) > 11:
        digits = digits[2:]

    # Validate length (should be 10 or 11 digits: DDD + number)
    if len(digits) < 10 or len(digits) > 11:
        return None

    # Extract area code and local number
    area_code = digits[:2]
    local_number = digits[2:]

    # Check if it's a valid Brazilian area code
    if area_code not in BRAZIL_AREA_CODES:
        # Not a recognized area code, return as-is with country code
        return f"{whatsapp_prefix}+55{digits}"

    # Mobile numbers have 9 digits, landlines have 8 digits
    # 8-digit number starting with 9/8/7/6 is a mobile missing the 9th digit
    if len(local_number) == 8 and local_number[0] in BRAZIL_MOBILE_PREFIXES:
        local_number = "9" + local_number

    return f"{whatsapp_prefix}+{BRAZIL_COUNTRY_CODE}{area_code}{local_number}"


def denormalize_brazil_phone(phone: str | None) -> str | None:
    """Convert a 9-digit mobile number back to 8-digit format.

    This is used as a fallback when the normalized 9-digit format
    doesn't work (some WhatsApp accounts registered with old format).

    Args:
        phone: Normalized phone number (+5511999999999)

    Returns:
        8-digit format (+551199999999) or original if not applicable

    Examples:
        >>> denormalize_brazil_phone("+5551998644323")
        '+555198644323'
        >>> denormalize_brazil_phone("+555133224455")
        '+555133224455'
    """
    if not phone:
        return None

    phone = phone.strip()

    # Handle WhatsApp prefix
    whatsapp_prefix = ""
    if phone.lower().startswith("whatsapp:"):
        whatsapp_prefix = "whatsapp:"
        phone = phone[9:]

    # Extract digits only
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None

    # Must be Brazilian number with country code and 9-digit mobile
    if not digits.startswith("55") or len(digits) != 13:
        return f"{whatsapp_prefix}{phone}" if whatsapp_prefix else phone

    area_code = digits[2:4]
    local_number = digits[4:]

    # Only convert if it's a 9-digit mobile (starts with 99, 98, 97, 96)
    if len(local_number) == 9 and local_number[0] == "9" and local_number[1] in BRAZIL_MOBILE_PREFIXES:
        # Remove the leading 9 to get 8-digit format
        local_number = local_number[1:]
        return f"{whatsapp_prefix}+{BRAZIL_COUNTRY_CODE}{area_code}{local_number}"

    return f"{whatsapp_prefix}{phone}" if whatsapp_prefix else phone


def phones_match_brazil(phone1: str | None, phone2: str | None) -> bool:
    """Check if two phone numbers match after Brazilian normalization.

    Handles the 9th digit discrepancy by normalizing both before comparison.

    Args:
        phone1: First phone number
        phone2: Second phone number

    Returns:
        True if both normalize to the same number

    Examples:
        >>> phones_match_brazil("+555198644323", "+5551998644323")
        True
        >>> phones_match_brazil("5198644323", "+5551998644323")
        True
    """
    if not phone1 or not phone2:
        return False

    norm1 = normalize_brazil_phone(phone1)
    norm2 = normalize_brazil_phone(phone2)

    if not norm1 or not norm2:
        return False

    return norm1 == norm2
