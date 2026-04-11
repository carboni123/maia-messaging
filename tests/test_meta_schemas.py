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
