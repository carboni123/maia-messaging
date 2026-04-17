"""Email delivery providers.

Concrete providers must be imported from their module to keep
third-party SDK dependencies optional::

    from messaging.email.smtp2go import Smtp2GoProvider    # httpx (always available)
    from messaging.email.sendgrid import SendGridProvider  # requires `maia-messaging[sendgrid]`
"""

from .base import EmailProvider

__all__ = ["EmailProvider"]
