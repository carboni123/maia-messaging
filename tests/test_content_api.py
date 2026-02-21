"""Tests for the Twilio Content API module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from messaging import TwilioConfig
from messaging.content_api import (
    TwilioContentAPI,
    TwilioContentAPIError,
    TwilioTemplateResponse,
    format_types_for_content_api,
)


def _make_api(config: TwilioConfig) -> TwilioContentAPI:
    """Create a TwilioContentAPI with a mocked Client."""
    with patch("messaging.content_api.Client"), \
         patch("messaging.content_api.TwilioHttpClient"):
        return TwilioContentAPI(config)


# ── format_types_for_content_api ─────────────────────────────────────


class TestFormatTypes:
    def test_renames_underscore_keys(self):
        result = format_types_for_content_api({"twilio_text": {"body": "hi"}})
        assert "twilio/text" in result
        assert "twilio_text" not in result

    def test_preserves_slash_keys(self):
        result = format_types_for_content_api({"twilio/text": {"body": "hi"}})
        assert "twilio/text" in result

    def test_renames_quick_reply(self):
        result = format_types_for_content_api({"twilio_quick_reply": {"body": "hi"}})
        assert "twilio/quick-reply" in result

    def test_renames_whatsapp_types(self):
        result = format_types_for_content_api({"whatsapp_card": {}})
        assert "whatsapp/card" in result


# ── TwilioTemplateResponse ───────────────────────────────────────────


class TestTwilioTemplateResponse:
    def test_from_dict_basic(self):
        data = {"sid": "HX123", "friendly_name": "test", "language": "en"}
        resp = TwilioTemplateResponse.from_dict(data)
        assert resp.sid == "HX123"
        assert resp.friendly_name == "test"
        assert resp.language == "en"

    def test_from_dict_extracts_approval_status(self):
        data = {
            "sid": "HX123",
            "friendly_name": "test",
            "approval_requests": {"status": "approved", "name": "my_template"},
        }
        resp = TwilioTemplateResponse.from_dict(data)
        assert resp.status == "approved"
        assert resp.template_name == "my_template"

    def test_to_dict_round_trip(self):
        data = {
            "sid": "HX123",
            "friendly_name": "test",
            "language": "en",
            "status": "approved",
        }
        resp = TwilioTemplateResponse.from_dict(data)
        output = resp.to_dict()
        assert output["sid"] == "HX123"
        assert output["status"] == "approved"

    def test_to_dict_excludes_none_fields(self):
        data = {"sid": "HX123", "friendly_name": "test"}
        resp = TwilioTemplateResponse.from_dict(data)
        output = resp.to_dict()
        assert "language" not in output
        assert "types" not in output


# ── TwilioContentAPI.create_template ─────────────────────────────────


class TestCreateTemplate:
    def test_create_template_success(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX123", "friendly_name": "test_tpl"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        result = api.create_template(
            friendly_name="test_tpl",
            language="en",
            types={"twilio_text": {"body": "Hello {{1}}"}},
        )

        assert result["sid"] == "HX123"
        assert result["friendly_name"] == "test_tpl"

    def test_create_template_raises_on_error_response(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=400,
            content=json.dumps({"message": "Invalid content", "code": 50400}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        with pytest.raises(TwilioContentAPIError) as excinfo:
            api.create_template(
                friendly_name="bad_tpl",
                language="en",
                types={"twilio_text": {"body": "Hi"}},
            )
        assert "Invalid content" in str(excinfo.value)
        assert excinfo.value.status == 400

    def test_create_template_returns_data_when_sid_missing(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=200,
            content=json.dumps({"sid": "", "friendly_name": "test_tpl"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        result = api.create_template(
            friendly_name="test_tpl",
            language="en",
            types={"twilio_text": {"body": "Hi"}},
        )

        assert result["sid"] == ""
        assert result["friendly_name"] == "test_tpl"

    def test_create_template_deletes_existing_when_sid_provided(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX_NEW", "friendly_name": "test_tpl"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        mock_delete = MagicMock()
        mock_content_instance = MagicMock(delete=mock_delete)
        api._client.content.v1.contents = MagicMock(return_value=mock_content_instance)

        api.create_template(
            friendly_name="test_tpl",
            language="en",
            types={"twilio_text": {"body": "Hi"}},
            template_sid="HX_OLD",
        )

        mock_delete.assert_called_once()

    def test_create_template_rejects_unsupported_whatsapp_types(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX123", "friendly_name": "test_tpl"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        with pytest.raises(TwilioContentAPIError) as excinfo:
            api.create_template(
                friendly_name="test_tpl",
                language="en",
                types={"twilio_list_picker": {"body": "Hi"}},
                whatsapp_template_name="my_tpl",
            )
        assert "do not support" in str(excinfo.value)

    def test_create_template_handles_placeholder_variables(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX123", "friendly_name": "test_tpl"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        api.create_template(
            friendly_name="test_tpl",
            language="en",
            types={"twilio_text": {"body": "Hi {{1}}"}},
            variables={"placeholders": [{"index": 1, "example": "John"}]},
        )

        call_kwargs = api._client.request.call_args
        payload = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data", {})
        assert payload.get("variables") == {"1": "John"}


# ── TwilioContentAPI.get_template_status ─────────────────────────────


class TestGetTemplateStatus:
    def test_get_status_success(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_resource = MagicMock(
            sid="HX123",
            friendly_name="test_tpl",
            approval_status="approved",
            rejection_reason=None,
            spec=["sid", "friendly_name", "approval_status", "rejection_reason", "whatsapp_template_name"],
        )
        mock_resource.whatsapp_template_name = "my_tpl"
        # Ensure template_name attr does NOT exist so getattr falls through
        del mock_resource.template_name

        api._client.content.v1.contents = MagicMock(
            return_value=MagicMock(fetch=MagicMock(return_value=mock_resource))
        )

        result = api.get_template_status(template_sid="HX123")
        assert result["sid"] == "HX123"
        assert result["status"] == "approved"
        assert result["template_name"] == "my_tpl"

    def test_get_status_raises_on_api_error(self, twilio_config: TwilioConfig):
        from twilio.base.exceptions import TwilioRestException

        api = _make_api(twilio_config)
        api._client.content.v1.contents = MagicMock(
            return_value=MagicMock(
                fetch=MagicMock(
                    side_effect=TwilioRestException(404, "https://content.twilio.com", msg="Not found")
                )
            )
        )

        with pytest.raises(TwilioContentAPIError):
            api.get_template_status(template_sid="HX_NONEXISTENT")


# ── TwilioContentAPI.list_templates ──────────────────────────────────


class TestListTemplates:
    def test_list_templates_success(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_resource_1 = MagicMock(
            sid="HX1", friendly_name="tpl_1", language="en",
            types=None, variables=None, approval_requests=None,
        )
        mock_resource_2 = MagicMock(
            sid="HX2", friendly_name="tpl_2", language="pt",
            types=None, variables=None, approval_requests={"status": "pending"},
        )
        api._client.content.v1.content_and_approvals.stream = MagicMock(
            return_value=[mock_resource_1, mock_resource_2]
        )

        result = api.list_templates()
        assert len(result) == 2
        assert result[0]["sid"] == "HX1"
        assert result[1]["approval_requests"] == {"status": "pending"}

    def test_list_templates_empty(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        api._client.content.v1.content_and_approvals.stream = MagicMock(return_value=[])

        result = api.list_templates()
        assert result == []


# ── TwilioContentAPI.create_quick_reply ──────────────────────────────


class TestCreateQuickReply:
    def test_create_quick_reply_success(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX_QR_123"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        result = api.create_quick_reply(
            body="Choose an option:",
            buttons=[
                {"id": "btn_1", "title": "Option A"},
                {"id": "btn_2", "title": "Option B"},
            ],
        )

        assert result["sid"] == "HX_QR_123"
        assert result["status"] == "created"
        assert result["friendly_name"].startswith("quick_reply_")

    def test_create_quick_reply_with_header(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX_QR_456"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        api.create_quick_reply(
            body="Choose an option:",
            buttons=[{"id": "btn_1", "title": "Yes"}],
            header="Important",
        )

        call_kwargs = api._client.request.call_args
        payload = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data", {})
        types = payload.get("types", {})
        assert "twilio/quick-reply" in types
        assert "twilio/text" in types

    def test_create_quick_reply_limits_buttons_to_3(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=201,
            content=json.dumps({"sid": "HX_QR_789"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        api.create_quick_reply(
            body="Pick one:",
            buttons=[
                {"id": f"btn_{i}", "title": f"Option {i}"}
                for i in range(5)
            ],
        )

        call_kwargs = api._client.request.call_args
        payload = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data", {})
        quick_reply = payload["types"]["twilio/quick-reply"]
        assert len(quick_reply["actions"]) == 3

    def test_create_quick_reply_raises_on_api_error(self, twilio_config: TwilioConfig):
        api = _make_api(twilio_config)
        mock_response = MagicMock(
            status_code=422,
            content=json.dumps({"message": "Invalid quick-reply"}).encode(),
        )
        api._client.request = MagicMock(return_value=mock_response)

        with pytest.raises(TwilioContentAPIError) as excinfo:
            api.create_quick_reply(
                body="Pick one:",
                buttons=[{"id": "btn_1", "title": "Yes"}],
            )
        assert "Invalid quick-reply" in str(excinfo.value)


# ── TwilioContentAPIError ────────────────────────────────────────────


class TestTwilioContentAPIError:
    def test_error_stores_metadata(self):
        err = TwilioContentAPIError("Something broke", status=400, code=50400)
        assert str(err) == "Something broke"
        assert err.status == 400
        assert err.code == 50400

    def test_error_defaults(self):
        err = TwilioContentAPIError("Generic error")
        assert err.status is None
        assert err.code is None
