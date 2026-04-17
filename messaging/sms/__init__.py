"""SMS channel — multi-provider SMS delivery.

Concrete providers must be imported from their module to keep
third-party SDK dependencies optional::

    from messaging.sms.twilio import TwilioSMSProvider  # requires `maia-messaging[twilio]`
"""

from .base import SMSProvider

__all__ = ["SMSProvider"]
