"""Telegram channel providers.

Concrete providers must be imported from their module::

    from messaging.telegram.bot_api import TelegramBotProvider  # httpx (always available)
"""

from .base import TelegramMessage, TelegramProvider
from .schemas import (
    TelegramErrorResponse,
    TelegramMediaPayload,
    TelegramResultMessage,
    TelegramSuccessResponse,
    TelegramTextPayload,
)

__all__ = [
    "TelegramMessage",
    "TelegramProvider",
    # Telegram Bot API schemas
    "TelegramErrorResponse",
    "TelegramMediaPayload",
    "TelegramResultMessage",
    "TelegramSuccessResponse",
    "TelegramTextPayload",
]
