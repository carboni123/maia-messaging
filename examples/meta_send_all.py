"""Send every Meta WhatsApp message type — manual testing script.

Usage:
    cp examples/.env.example examples/.env  # fill in your credentials
    python examples/meta_send_all.py              # send all types
    python examples/meta_send_all.py text media    # send specific types
    python examples/meta_send_all.py --list        # list available types
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the examples directory
load_dotenv(Path(__file__).parent / ".env")

from messaging import (
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    WhatsAppContacts,
    WhatsAppInteractiveCTA,
    WhatsAppInteractiveList,
    WhatsAppInteractiveReply,
    WhatsAppLocation,
    WhatsAppMedia,
    WhatsAppProduct,
    WhatsAppProductList,
    WhatsAppReaction,
    WhatsAppSticker,
    WhatsAppText,
)
from messaging.providers.meta import MetaWhatsAppProvider


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def send_text(provider: MetaWhatsAppProvider, to: str):
    return provider.send(WhatsAppText(to=to, body="Hello from maia-messaging!"))


def send_media(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppMedia(
            to=to,
            media_urls=["https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"],
            media_types=["image/png"],
            caption="Test image from maia-messaging",
        )
    )


def send_template(provider: MetaWhatsAppProvider, to: str):
    """Sends the 'hello_world' template — exists by default on all WABA accounts."""
    return provider.send(
        MetaWhatsAppTemplate(
            to=to,
            template_name="hello_world",
            language_code="en_US",
        )
    )


def send_reply_buttons(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppInteractiveReply(
            to=to,
            body="How was your experience?",
            buttons=[
                {"id": "btn_great", "title": "Great"},
                {"id": "btn_ok", "title": "OK"},
                {"id": "btn_bad", "title": "Bad"},
            ],
        )
    )


def send_list(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppInteractiveList(
            to=to,
            body="What can we help you with?",
            button="View options",
            header="Support Menu",
            footer="Reply anytime",
            sections=[
                {
                    "title": "Account",
                    "rows": [
                        {"id": "billing", "title": "Billing", "description": "Invoices and payments"},
                        {"id": "password", "title": "Reset password"},
                    ],
                },
                {
                    "title": "Orders",
                    "rows": [
                        {"id": "track", "title": "Track order", "description": "Check delivery status"},
                        {"id": "return", "title": "Return item"},
                    ],
                },
            ],
        )
    )


def send_cta(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppInteractiveCTA(
            to=to,
            body="Visit our website to learn more about maia-messaging.",
            display_text="Open website",
            url="https://github.com/carboni123/maia-messaging",
            header="Check it out",
        )
    )


def send_product(provider: MetaWhatsAppProvider, to: str):
    catalog_id = env("META_TEST_CATALOG_ID")
    product_id = env("META_TEST_PRODUCT_ID")
    if not catalog_id or not product_id:
        print("  SKIP: set META_TEST_CATALOG_ID and META_TEST_PRODUCT_ID")
        return None
    return provider.send(
        WhatsAppProduct(
            to=to,
            body="Check out this product!",
            catalog_id=catalog_id,
            product_retailer_id=product_id,
        )
    )


def send_product_list(provider: MetaWhatsAppProvider, to: str):
    catalog_id = env("META_TEST_CATALOG_ID")
    product_id = env("META_TEST_PRODUCT_ID")
    if not catalog_id or not product_id:
        print("  SKIP: set META_TEST_CATALOG_ID and META_TEST_PRODUCT_ID")
        return None
    return provider.send(
        WhatsAppProductList(
            to=to,
            body="Browse our collection",
            header="Featured Products",
            catalog_id=catalog_id,
            sections=[
                {
                    "title": "Popular",
                    "product_items": [{"product_retailer_id": product_id}],
                },
            ],
        )
    )


def send_location(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppLocation(
            to=to,
            latitude=-23.5505,
            longitude=-46.6333,
            name="Sao Paulo",
            address="Sao Paulo, SP, Brazil",
        )
    )


def send_contacts(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppContacts(
            to=to,
            contacts=[
                {
                    "name": {"formatted_name": "Maia Support", "first_name": "Maia", "last_name": "Support"},
                    "phones": [{"phone": "+14155238886", "type": "WORK"}],
                    "emails": [{"email": "support@example.com", "type": "WORK"}],
                    "org": {"company": "Maia Messaging"},
                },
            ],
        )
    )


def send_reaction(provider: MetaWhatsAppProvider, to: str):
    wamid = env("META_TEST_WAMID")
    if not wamid:
        print("  SKIP: set META_TEST_WAMID to an existing message ID")
        return None
    return provider.send(
        WhatsAppReaction(
            to=to,
            message_id=wamid,
            emoji="\U0001f44d",  # thumbs up
        )
    )


def send_sticker(provider: MetaWhatsAppProvider, to: str):
    return provider.send(
        WhatsAppSticker(
            to=to,
            # Must be 512x512 .webp — WhatsApp sticker requirement
            sticker="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/512px-WhatsApp.svg.png.webp",
        )
    )


SENDERS: dict[str, tuple[str, callable]] = {
    "text":           ("Text message",         send_text),
    "media":          ("Media (image)",         send_media),
    "template":       ("Template (hello_world)", send_template),
    "reply_buttons":  ("Reply buttons (3)",     send_reply_buttons),
    "list":           ("List menu",             send_list),
    "cta":            ("CTA URL button",        send_cta),
    "product":        ("Single product",        send_product),
    "product_list":   ("Product list",          send_product_list),
    "location":       ("Location pin",          send_location),
    "contacts":       ("Contact card",          send_contacts),
    "reaction":       ("Reaction emoji",        send_reaction),
    "sticker":        ("Sticker",               send_sticker),
}


def main():
    if "--list" in sys.argv:
        print("Available message types:")
        for key, (label, _) in SENDERS.items():
            print(f"  {key:16s} {label}")
        return

    phone_number_id = env("META_PHONE_NUMBER_ID")
    access_token = env("META_ACCESS_TOKEN")
    recipient = env("META_TEST_RECIPIENT")

    if not phone_number_id or not access_token or not recipient:
        print("Set these environment variables first:")
        print("  META_PHONE_NUMBER_ID  — your WABA phone number ID")
        print("  META_ACCESS_TOKEN     — Meta Cloud API access token")
        print("  META_TEST_RECIPIENT   — phone number to send to (E.164)")
        sys.exit(1)

    provider = MetaWhatsAppProvider(
        MetaWhatsAppConfig(
            phone_number_id=phone_number_id,
            access_token=access_token,
        )
    )

    # Pick which types to send
    requested = sys.argv[1:]
    if not requested:
        requested = list(SENDERS.keys())

    unknown = [r for r in requested if r not in SENDERS]
    if unknown:
        print(f"Unknown types: {', '.join(unknown)}")
        print(f"Run with --list to see available types")
        sys.exit(1)

    results = []
    for key in requested:
        label, sender = SENDERS[key]
        print(f"\n--- {label} ---")
        result = sender(provider, recipient)
        if result is None:
            results.append((key, "SKIPPED", ""))
            continue
        status = "OK" if result.succeeded else "FAIL"
        detail = result.external_id or result.error_message or ""
        print(f"  {status}: {detail}")
        results.append((key, status, detail))
        time.sleep(1)  # gentle rate limiting

    provider.close()

    # Summary
    print(f"\n{'=' * 50}")
    print(f"{'Type':16s} {'Status':8s} Detail")
    print(f"{'-' * 50}")
    for key, status, detail in results:
        print(f"{key:16s} {status:8s} {detail}")


if __name__ == "__main__":
    main()
