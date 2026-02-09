"""WhatsApp template message pricing calculator.

Calculates per-message costs for WhatsApp template messages based on category.
Pricing is based on Meta's Business API rates for Brazil (default market).
"""

from decimal import Decimal

# WhatsApp template pricing by category (USD per message)
# Default pricing based on Brazil rates (as of 2024)
# See: https://developers.facebook.com/docs/whatsapp/pricing
TEMPLATE_PRICING: dict[str | None, Decimal] = {
    "MARKETING": Decimal("0.0600"),
    "UTILITY": Decimal("0.0200"),
    "AUTHENTICATION": Decimal("0.0150"),
    None: Decimal("0.0200"),  # Default to utility pricing
}


def calculate_template_cost(category: str | None) -> Decimal:
    """Calculate cost for sending a WhatsApp template message.

    Args:
        category: The template category string (MARKETING, UTILITY, AUTHENTICATION, or None)

    Returns:
        Cost in USD as a Decimal
    """
    key = category.upper() if category else None
    return TEMPLATE_PRICING.get(key, TEMPLATE_PRICING[None])
