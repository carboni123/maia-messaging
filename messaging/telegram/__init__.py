"""Telegram channel providers."""

from .base import TelegramMessage, TelegramProvider
from .bot_api import TelegramBotProvider
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
    "TelegramBotProvider",
    # Telegram Bot API schemas
    "TelegramErrorResponse",
    "TelegramMediaPayload",
    "TelegramResultMessage",
    "TelegramSuccessResponse",
    "TelegramTextPayload",
]
