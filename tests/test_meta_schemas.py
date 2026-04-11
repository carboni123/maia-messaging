"""Tests for Meta WhatsApp Cloud API Pydantic schemas."""

import pytest
from pydantic import ValidationError

from messaging.providers.meta_schemas import (
    MetaErrorResponse,
    MetaMediaMessage,
    MetaMediaObject,
    MetaMessageEntry,
    MetaMessageResponse,
    MetaTemplateComponentPayload,
    MetaTemplateLanguage,
    MetaTemplateMessage,
    MetaTemplateParameter,
    MetaTemplatePayload,
    MetaTextBody,
    MetaTextMessage,
)


class TestMetaTextModels:
    def test_text_message_serializes_correctly(self):
        msg = MetaTextMessage(to="5511999999999", text=MetaTextBody(body="Hello"))
        payload = msg.model_dump()
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "text",
            "text": {"body": "Hello"},
        }

    def test_text_message_defaults(self):
        msg = MetaTextMessage(to="123", text=MetaTextBody(body="hi"))
        assert msg.messaging_product == "whatsapp"
        assert msg.type == "text"


class TestMetaMediaModels:
    def test_image_message_excludes_none_fields(self):
        msg = MetaMediaMessage(
            to="5511999999999",
            type="image",
            image=MetaMediaObject(link="https://example.com/photo.jpg", caption="Look!"),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "image"
        assert payload["image"] == {"link": "https://example.com/photo.jpg", "caption": "Look!"}
        assert "video" not in payload
        assert "audio" not in payload
        assert "document" not in payload

    def test_document_without_caption(self):
        msg = MetaMediaMessage(
            to="5511999999999",
            type="document",
            document=MetaMediaObject(link="https://example.com/report.pdf"),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "document"
        assert payload["document"] == {"link": "https://example.com/report.pdf"}
        assert "caption" not in payload["document"]


class TestMetaTemplateModels:
    def test_template_message_with_components(self):
        msg = MetaTemplateMessage(
            to="5511999999999",
            template=MetaTemplatePayload(
                name="order_update",
                language=MetaTemplateLanguage(code="en_US"),
                components=[
                    MetaTemplateComponentPayload(
                        type="body",
                        parameters=[
                            MetaTemplateParameter(type="text", text="John"),
                            MetaTemplateParameter(text="Order #42"),
                        ],
                    )
                ],
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_update"
        assert payload["template"]["language"]["code"] == "en_US"
        assert len(payload["template"]["components"]) == 1
        assert payload["template"]["components"][0]["parameters"][1]["type"] == "text"

    def test_template_without_components(self):
        msg = MetaTemplateMessage(
            to="5511999999999",
            template=MetaTemplatePayload(
                name="hello_world",
                language=MetaTemplateLanguage(code="en_US"),
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert "components" not in payload["template"]

    def test_parameter_default_type_is_text(self):
        param = MetaTemplateParameter(text="hello")
        assert param.type == "text"

    def test_component_accepts_any_type(self):
        comp = MetaTemplateComponentPayload(
            type="header",
            parameters=[MetaTemplateParameter(type="image", text="https://example.com/img.jpg")],
        )
        assert comp.type == "header"


class TestMetaInteractiveModels:
    def test_interactive_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveAction,
            MetaInteractiveBody,
            MetaInteractiveMessage,
            MetaInteractivePayload,
            MetaReplyButton,
        )

        msg = MetaInteractiveMessage(
            to="5511999999999",
            interactive=MetaInteractivePayload(
                body=MetaInteractiveBody(text="Choose an option:"),
                action=MetaInteractiveAction(
                    buttons=[
                        MetaReplyButton(reply={"id": "opt_yes", "title": "Yes"}),
                        MetaReplyButton(reply={"id": "opt_no", "title": "No"}),
                    ]
                ),
            ),
        )
        payload = msg.model_dump()
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "Choose an option:"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "opt_yes", "title": "Yes"}},
                        {"type": "reply", "reply": {"id": "opt_no", "title": "No"}},
                    ]
                },
            },
        }

    def test_interactive_message_defaults(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveAction,
            MetaInteractiveBody,
            MetaInteractiveMessage,
            MetaInteractivePayload,
            MetaReplyButton,
        )

        msg = MetaInteractiveMessage(
            to="123",
            interactive=MetaInteractivePayload(
                body=MetaInteractiveBody(text="hi"),
                action=MetaInteractiveAction(buttons=[MetaReplyButton(reply={"id": "1", "title": "OK"})]),
            ),
        )
        assert msg.messaging_product == "whatsapp"
        assert msg.type == "interactive"
        assert msg.interactive.type == "button"

    def test_reply_button_default_type(self):
        from messaging.providers.meta_schemas import MetaReplyButton

        btn = MetaReplyButton(reply={"id": "1", "title": "OK"})
        assert btn.type == "reply"


class TestMetaListModels:
    def test_list_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveBody,
            MetaInteractiveFooter,
            MetaInteractiveHeader,
            MetaListAction,
            MetaListMessage,
            MetaListPayload,
            MetaListRow,
            MetaListSection,
        )

        msg = MetaListMessage(
            to="5511999999999",
            interactive=MetaListPayload(
                header=MetaInteractiveHeader(text="Our Menu"),
                body=MetaInteractiveBody(text="Pick a dish:"),
                footer=MetaInteractiveFooter(text="Powered by Maia"),
                action=MetaListAction(
                    button="View options",
                    sections=[
                        MetaListSection(
                            title="Main Courses",
                            rows=[
                                MetaListRow(id="pasta", title="Pasta", description="Fresh homemade pasta"),
                                MetaListRow(id="salad", title="Salad"),
                            ],
                        )
                    ],
                ),
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Our Menu"},
                "body": {"text": "Pick a dish:"},
                "footer": {"text": "Powered by Maia"},
                "action": {
                    "button": "View options",
                    "sections": [
                        {
                            "title": "Main Courses",
                            "rows": [
                                {"id": "pasta", "title": "Pasta", "description": "Fresh homemade pasta"},
                                {"id": "salad", "title": "Salad"},
                            ],
                        }
                    ],
                },
            },
        }

    def test_list_payload_defaults(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveBody,
            MetaListAction,
            MetaListPayload,
            MetaListRow,
            MetaListSection,
        )

        payload = MetaListPayload(
            body=MetaInteractiveBody(text="hi"),
            action=MetaListAction(
                button="Menu",
                sections=[MetaListSection(rows=[MetaListRow(id="1", title="One")])],
            ),
        )
        assert payload.type == "list"

    def test_list_row_optional_description(self):
        from messaging.providers.meta_schemas import MetaListRow

        row = MetaListRow(id="r1", title="Row 1")
        assert row.description is None


class TestMetaCTAModels:
    def test_cta_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaCTAAction,
            MetaCTAMessage,
            MetaCTAParameters,
            MetaCTAPayload,
            MetaInteractiveBody,
        )

        msg = MetaCTAMessage(
            to="5511999999999",
            interactive=MetaCTAPayload(
                body=MetaInteractiveBody(text="Visit our site"),
                action=MetaCTAAction(
                    parameters=MetaCTAParameters(
                        display_text="Open Website",
                        url="https://example.com",
                    ),
                ),
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "body": {"text": "Visit our site"},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": "Open Website",
                        "url": "https://example.com",
                    },
                },
            },
        }

    def test_cta_action_default_name(self):
        from messaging.providers.meta_schemas import MetaCTAAction, MetaCTAParameters

        action = MetaCTAAction(
            parameters=MetaCTAParameters(display_text="Click", url="https://example.com"),
        )
        assert action.name == "cta_url"


class TestMetaProductModels:
    def test_product_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveBody,
            MetaProductAction,
            MetaProductMessage,
            MetaProductPayload,
        )

        msg = MetaProductMessage(
            to="5511999999999",
            interactive=MetaProductPayload(
                body=MetaInteractiveBody(text="Check out this product"),
                action=MetaProductAction(
                    catalog_id="CAT123",
                    product_retailer_id="SKU456",
                ),
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "interactive",
            "interactive": {
                "type": "product",
                "body": {"text": "Check out this product"},
                "action": {
                    "catalog_id": "CAT123",
                    "product_retailer_id": "SKU456",
                },
            },
        }


class TestMetaProductListModels:
    def test_product_list_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaInteractiveBody,
            MetaInteractiveHeader,
            MetaProductItem,
            MetaProductListAction,
            MetaProductListMessage,
            MetaProductListPayload,
            MetaProductSection,
        )

        msg = MetaProductListMessage(
            to="5511999999999",
            interactive=MetaProductListPayload(
                header=MetaInteractiveHeader(text="Our Catalog"),
                body=MetaInteractiveBody(text="Browse our products"),
                action=MetaProductListAction(
                    catalog_id="CAT789",
                    sections=[
                        MetaProductSection(
                            title="Electronics",
                            product_items=[
                                MetaProductItem(product_retailer_id="PHONE01"),
                                MetaProductItem(product_retailer_id="LAPTOP02"),
                            ],
                        )
                    ],
                ),
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload == {
            "messaging_product": "whatsapp",
            "to": "5511999999999",
            "type": "interactive",
            "interactive": {
                "type": "product_list",
                "header": {"type": "text", "text": "Our Catalog"},
                "body": {"text": "Browse our products"},
                "action": {
                    "catalog_id": "CAT789",
                    "sections": [
                        {
                            "title": "Electronics",
                            "product_items": [
                                {"product_retailer_id": "PHONE01"},
                                {"product_retailer_id": "LAPTOP02"},
                            ],
                        }
                    ],
                },
            },
        }

    def test_product_item_minimal(self):
        from messaging.providers.meta_schemas import MetaProductItem

        item = MetaProductItem(product_retailer_id="SKU001")
        assert item.product_retailer_id == "SKU001"


class TestMetaLocationModels:
    def test_location_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import MetaLocationCoordinates, MetaLocationMessage

        msg = MetaLocationMessage(
            to="5511999999999",
            location=MetaLocationCoordinates(
                latitude=-23.5505, longitude=-46.6333, name="São Paulo", address="SP, Brazil"
            ),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["messaging_product"] == "whatsapp"
        assert payload["type"] == "location"
        assert payload["location"]["latitude"] == -23.5505
        assert payload["location"]["longitude"] == -46.6333
        assert payload["location"]["name"] == "São Paulo"
        assert payload["location"]["address"] == "SP, Brazil"

    def test_location_without_optional_fields(self):
        from messaging.providers.meta_schemas import MetaLocationCoordinates, MetaLocationMessage

        msg = MetaLocationMessage(
            to="123",
            location=MetaLocationCoordinates(latitude=0.0, longitude=0.0),
        )
        payload = msg.model_dump(exclude_none=True)
        assert "name" not in payload["location"]
        assert "address" not in payload["location"]


class TestMetaContactsModels:
    def test_contacts_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import (
            MetaContact,
            MetaContactEmail,
            MetaContactName,
            MetaContactOrg,
            MetaContactPhone,
            MetaContactsMessage,
            MetaContactUrl,
        )

        msg = MetaContactsMessage(
            to="5511999999999",
            contacts=[
                MetaContact(
                    name=MetaContactName(formatted_name="John Doe", first_name="John"),
                    phones=[MetaContactPhone(phone="+5511999", type="CELL")],
                    emails=[MetaContactEmail(email="john@example.com", type="WORK")],
                    org=MetaContactOrg(company="Acme"),
                    urls=[MetaContactUrl(url="https://example.com")],
                )
            ],
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "contacts"
        contact = payload["contacts"][0]
        assert contact["name"]["formatted_name"] == "John Doe"
        assert contact["phones"][0]["phone"] == "+5511999"
        assert contact["emails"][0]["email"] == "john@example.com"
        assert contact["org"]["company"] == "Acme"
        assert contact["urls"][0]["url"] == "https://example.com"

    def test_contact_minimal(self):
        from messaging.providers.meta_schemas import MetaContact, MetaContactName, MetaContactsMessage

        msg = MetaContactsMessage(
            to="123",
            contacts=[MetaContact(name=MetaContactName(formatted_name="Jane"))],
        )
        payload = msg.model_dump(exclude_none=True)
        contact = payload["contacts"][0]
        assert "name" in contact
        assert "phones" not in contact
        assert "emails" not in contact
        assert "org" not in contact
        assert "urls" not in contact


class TestMetaReactionModels:
    def test_reaction_message_serializes_correctly(self):
        from messaging.providers.meta_schemas import MetaReactionMessage, MetaReactionPayload

        msg = MetaReactionMessage(
            to="5511999999999",
            reaction=MetaReactionPayload(message_id="wamid.xxx", emoji="\U0001f44d"),
        )
        payload = msg.model_dump()
        assert payload["type"] == "reaction"
        assert payload["reaction"]["message_id"] == "wamid.xxx"
        assert payload["reaction"]["emoji"] == "\U0001f44d"


class TestMetaStickerModels:
    def test_sticker_message_with_link(self):
        from messaging.providers.meta_schemas import MetaStickerMessage, MetaStickerObject

        msg = MetaStickerMessage(
            to="5511999999999",
            sticker=MetaStickerObject(link="https://example.com/sticker.webp"),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "sticker"
        assert payload["sticker"]["link"] == "https://example.com/sticker.webp"
        assert "id" not in payload["sticker"]

    def test_sticker_message_with_id(self):
        from messaging.providers.meta_schemas import MetaStickerMessage, MetaStickerObject

        msg = MetaStickerMessage(
            to="5511999999999",
            sticker=MetaStickerObject(id="media_123"),
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["type"] == "sticker"
        assert payload["sticker"]["id"] == "media_123"
        assert "link" not in payload["sticker"]


class TestMetaResponseModels:
    def test_success_response_parses(self):
        data = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
            "messages": [{"id": "wamid.HBgN"}],
        }
        resp = MetaMessageResponse.model_validate(data)
        assert resp.messages[0].id == "wamid.HBgN"
        assert resp.contacts[0].wa_id == "5511999999999"
        assert resp.contacts[0].input == "5511999999999"

    def test_message_entry_optional_status(self):
        entry = MetaMessageEntry(id="wamid.123")
        assert entry.message_status is None

    def test_error_response_parses(self):
        data = {
            "error": {
                "message": "Invalid parameter",
                "type": "OAuthException",
                "code": 100,
                "fbtrace_id": "ABC123",
            }
        }
        resp = MetaErrorResponse.model_validate(data)
        assert resp.error.code == 100
        assert resp.error.message == "Invalid parameter"

    def test_error_response_optional_fields(self):
        data = {"error": {"message": "Something went wrong"}}
        resp = MetaErrorResponse.model_validate(data)
        assert resp.error.code is None
        assert resp.error.type is None

    def test_success_response_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            MetaMessageResponse.model_validate({"messaging_product": "whatsapp"})
