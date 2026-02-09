"""Phone normalization utilities."""

from .brazil import denormalize_brazil_phone, normalize_brazil_phone, phones_match_brazil
from .normalize import (
    denormalize_phone_for_whatsapp,
    format_whatsapp_number,
    normalize_phone,
    normalize_whatsapp_id,
    phones_match,
)

__all__ = [
    "denormalize_brazil_phone",
    "denormalize_phone_for_whatsapp",
    "format_whatsapp_number",
    "normalize_brazil_phone",
    "normalize_phone",
    "normalize_whatsapp_id",
    "phones_match",
    "phones_match_brazil",
]
