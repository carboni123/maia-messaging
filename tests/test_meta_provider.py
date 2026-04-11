"""Tests for the Meta WhatsApp Cloud API provider."""

from unittest.mock import MagicMock

import pytest

from messaging import (
    DeliveryStatus,
    MetaWhatsAppConfig,
    MetaWhatsAppTemplate,
    WhatsAppInteractiveCTA,
    WhatsAppInteractiveList,
    WhatsAppInteractiveReply,
    WhatsAppMedia,
    WhatsAppProduct,
    WhatsAppProductList,
    WhatsAppTemplate,
    WhatsAppText,
)
from messaging.providers.meta import MetaWhatsAppProvider, _normalize_recipient


def _make_provider(
    config: MetaWhatsAppConfig, mock_response: MagicMock | None = None
) -> tuple[MetaWhatsAppProvider, MagicMock]:
    """Create a provider with a mocked httpx client."""
    provider = MetaWhatsAppProvider(config)
    mock_client = MagicMock()
    if mock_response is not None:
        mock_client.post = MagicMock(return_value=mock_response)
    provider._client = mock_client
    return provider, mock_client


def _ok_response(wamid: str = "wamid.HBgN") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
        "messages": [{"id": wamid}],
    }
    return resp


def _error_response(code: int = 100, message: str = "Invalid parameter") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "error": {
            "message": message,
            "type": "OAuthException",
            "code": code,
            "fbtrace_id": "ABC123",
        }
    }
    return resp


class TestMetaWhatsAppProviderInit:
    def test_raises_on_empty_phone_number_id(self):
        with pytest.raises(ValueError, match="phone_number_id is required"):
            MetaWhatsAppProvider(MetaWhatsAppConfig(phone_number_id="", access_token="token"))

    def test_raises_on_empty_access_token(self):
        with pytest.raises(ValueError, match="access_token is required"):
            MetaWhatsAppProvider(MetaWhatsAppConfig(phone_number_id="123", access_token=""))

    def test_constructs_correct_url(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        assert "123456789" in provider._url
        assert "/v21.0/" in provider._url
        assert provider._url.endswith("/messages")


class TestNormalizeRecipient:
    def test_strips_whatsapp_prefix_and_plus(self):
        assert _normalize_recipient("whatsapp:+5511999999999") == "5511999999999"

    def test_strips_plus_only(self):
        assert _normalize_recipient("+5511999999999") == "5511999999999"

    def test_plain_number_unchanged(self):
        assert _normalize_recipient("5511999999999") == "5511999999999"

    def test_case_insensitive_prefix(self):
        assert _normalize_recipient("WhatsApp:+14155238886") == "14155238886"

    def test_bsuid_passed_through(self):
        assert _normalize_recipient("BR.1A2B3C4D5E6F") == "BR.1A2B3C4D5E6F"

    def test_bsuid_with_whatsapp_prefix(self):
        assert _normalize_recipient("whatsapp:BR.1A2B3C4D5E6F") == "BR.1A2B3C4D5E6F"


class TestSendText:
    def test_send_text_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.text123"))

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello!"))

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.text123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello!"

    def test_send_text_strips_whatsapp_prefix(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hi"))

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "5511999999999"

    def test_send_empty_text_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(WhatsAppText(to="+5511999999999", body="   "))
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_text_includes_auth_header(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(WhatsAppText(to="+5511999999999", body="test"))

        headers = mock_client.post.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {meta_whatsapp_config.access_token}"


class TestSendMedia:
    def test_send_photo_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.photo123"))

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/photo.jpg"],
                media_types=["image/jpeg"],
                caption="Look!",
            )
        )

        assert result.succeeded
        assert result.external_id == "wamid.photo123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "image"
        assert payload["image"]["link"] == "https://example.com/photo.jpg"
        assert payload["image"]["caption"] == "Look!"

    def test_send_document_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/report.pdf"],
                media_types=["application/pdf"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "document"
        assert payload["document"]["link"] == "https://example.com/report.pdf"
        assert "caption" not in payload["document"]

    def test_send_video_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/clip.mp4"],
                media_types=["video/mp4"],
                caption="Watch this",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "video"
        assert payload["video"]["link"] == "https://example.com/clip.mp4"

    def test_send_audio_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/voice.ogg"],
                media_types=["audio/ogg"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "audio"

    def test_unknown_mime_defaults_to_document(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/file.xyz"],
                media_types=["application/octet-stream"],
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "document"

    def test_no_media_urls_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(WhatsAppMedia(to="+5511999999999", media_urls=[]))
        assert not result.succeeded
        assert "No media URLs" in result.error_message

    def test_multiple_media_urls_each_sent(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.last"))

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=[
                    "https://example.com/photo.jpg",
                    "https://example.com/doc.pdf",
                ],
                media_types=["image/jpeg", "application/pdf"],
                caption="See attached",
            )
        )

        assert result.succeeded
        assert mock_client.post.call_count == 2

        # First call: image with caption
        first_payload = mock_client.post.call_args_list[0].kwargs["json"]
        assert first_payload["type"] == "image"
        assert first_payload["image"]["caption"] == "See attached"

        # Second call: document without caption
        second_payload = mock_client.post.call_args_list[1].kwargs["json"]
        assert second_payload["type"] == "document"
        assert "caption" not in second_payload["document"]

    def test_multiple_media_partial_failure_returns_error(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok_response("wamid.first")
            return _error_response(400, "File too large")

        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=_side_effect)
        provider._client = mock_client

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/ok.jpg", "https://example.com/big.mp4"],
                media_types=["image/jpeg", "video/mp4"],
            )
        )

        assert not result.succeeded
        assert "File too large" in result.error_message

    def test_audio_caption_not_included(self, meta_whatsapp_config: MetaWhatsAppConfig):
        """Meta Cloud API does not support captions on audio messages."""
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            WhatsAppMedia(
                to="+5511999999999",
                media_urls=["https://example.com/voice.ogg"],
                media_types=["audio/ogg"],
                caption="This caption should be excluded",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "audio"
        assert "caption" not in payload["audio"]


class TestSendTemplate:
    def test_send_template_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.tmpl123"))

        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "John"},
                    {"type": "text", "text": "Order #42"},
                ],
            }
        ]

        result = provider.send(
            MetaWhatsAppTemplate(
                to="+5511999999999",
                template_name="order_update",
                language_code="en_US",
                components=components,
            )
        )

        assert result.succeeded
        assert result.external_id == "wamid.tmpl123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_update"
        assert payload["template"]["language"]["code"] == "en_US"
        assert payload["template"]["components"] == components

    def test_send_template_without_components(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(
            MetaWhatsAppTemplate(
                to="+5511999999999",
                template_name="hello_world",
                language_code="en_US",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert "components" not in payload["template"]

    def test_rejects_twilio_whatsapp_template(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppTemplate(to="+5511999999999", content_sid="HX123", content_variables={"1": "John"})
        )
        assert not result.succeeded
        assert "MetaWhatsAppTemplate" in result.error_message


class TestSendInteractive:
    def test_send_interactive_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.btn123"))

        result = provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="Choose an option:",
                buttons=[
                    {"id": "opt_1", "title": "Yes"},
                    {"id": "opt_2", "title": "No"},
                ],
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.btn123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "button"
        assert payload["interactive"]["body"]["text"] == "Choose an option:"
        buttons = payload["interactive"]["action"]["buttons"]
        assert len(buttons) == 2
        assert buttons[0]["reply"]["id"] == "opt_1"
        assert buttons[0]["reply"]["title"] == "Yes"
        assert buttons[1]["reply"]["id"] == "opt_2"
        assert buttons[1]["reply"]["title"] == "No"

    def test_send_interactive_strips_whatsapp_prefix(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(
            WhatsAppInteractiveReply(
                to="whatsapp:+5511999999999",
                body="Pick one",
                buttons=[{"id": "a", "title": "A"}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "5511999999999"

    def test_send_interactive_empty_body_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="   ",
                buttons=[{"id": "a", "title": "A"}],
            )
        )
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_interactive_no_buttons_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="Pick one",
                buttons=[],
            )
        )
        assert not result.succeeded
        assert "No buttons" in result.error_message

    def test_send_interactive_caps_at_three_buttons(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="Pick one",
                buttons=[
                    {"id": "1", "title": "One"},
                    {"id": "2", "title": "Two"},
                    {"id": "3", "title": "Three"},
                    {"id": "4", "title": "Four"},
                ],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        buttons = payload["interactive"]["action"]["buttons"]
        assert len(buttons) == 3
        assert buttons[2]["reply"]["id"] == "3"

    def test_send_interactive_truncates_title_at_20_chars(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="Pick",
                buttons=[{"id": "long", "title": "A" * 30}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        title = payload["interactive"]["action"]["buttons"][0]["reply"]["title"]
        assert len(title) == 20

    def test_send_interactive_truncates_body_at_1024_chars(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(
            WhatsAppInteractiveReply(
                to="+5511999999999",
                body="B" * 2000,
                buttons=[{"id": "a", "title": "OK"}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        assert len(payload["interactive"]["body"]["text"]) == 1024

    def test_send_interactive_with_bsuid(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        provider.send(
            WhatsAppInteractiveReply(
                to="BR.1A2B3C4D5E6F",
                body="Pick",
                buttons=[{"id": "a", "title": "OK"}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "BR.1A2B3C4D5E6F"


class TestSendList:
    def test_send_list_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.list123"))

        sections = [
            {
                "title": "Section 1",
                "rows": [
                    {"id": "1", "title": "Option 1", "description": "Desc"},
                    {"id": "2", "title": "Option 2", "description": "Desc 2"},
                ],
            }
        ]
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Pick from the list:",
                button="Menu",
                sections=sections,
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.list123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "list"
        assert payload["interactive"]["body"]["text"] == "Pick from the list:"
        assert payload["interactive"]["action"]["button"] == "Menu"
        action_sections = payload["interactive"]["action"]["sections"]
        assert len(action_sections) == 1
        assert action_sections[0]["title"] == "Section 1"
        assert len(action_sections[0]["rows"]) == 2
        assert action_sections[0]["rows"][0]["id"] == "1"
        assert action_sections[0]["rows"][0]["title"] == "Option 1"

    def test_send_list_with_header_and_footer(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        sections = [{"title": "S1", "rows": [{"id": "1", "title": "Row 1"}]}]
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body text",
                button="Open",
                sections=sections,
                header="My Header",
                footer="My Footer",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["interactive"]["header"]["text"] == "My Header"
        assert payload["interactive"]["footer"]["text"] == "My Footer"

    def test_send_list_empty_body_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="   ",
                button="Menu",
                sections=[{"title": "S", "rows": [{"id": "1", "title": "R"}]}],
            )
        )
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_list_no_button_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="",
                sections=[{"title": "S", "rows": [{"id": "1", "title": "R"}]}],
            )
        )
        assert not result.succeeded
        assert "No button text" in result.error_message

    def test_send_list_no_sections_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="Menu",
                sections=[],
            )
        )
        assert not result.succeeded
        assert "No sections" in result.error_message

    def test_send_list_no_rows_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="Menu",
                sections=[{"title": "Empty", "rows": []}],
            )
        )
        assert not result.succeeded
        assert "No rows" in result.error_message

    def test_send_list_too_many_rows_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        rows = [{"id": str(i), "title": f"Row {i}"} for i in range(11)]
        result = provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="Menu",
                sections=[{"title": "Big", "rows": rows}],
            )
        )
        assert not result.succeeded
        assert "Too many rows" in result.error_message

    def test_send_list_truncates_body_at_1024(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="B" * 2000,
                button="Menu",
                sections=[{"title": "S", "rows": [{"id": "1", "title": "R"}]}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        assert len(payload["interactive"]["body"]["text"]) == 1024

    def test_send_list_truncates_row_title_at_24(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="Menu",
                sections=[{"title": "S", "rows": [{"id": "1", "title": "A" * 40}]}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        row_title = payload["interactive"]["action"]["sections"][0]["rows"][0]["title"]
        assert len(row_title) == 24

    def test_send_list_truncates_button_at_20(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        provider.send(
            WhatsAppInteractiveList(
                to="+5511999999999",
                body="Body",
                button="B" * 30,
                sections=[{"title": "S", "rows": [{"id": "1", "title": "R"}]}],
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        assert len(payload["interactive"]["action"]["button"]) == 20


class TestSendCTA:
    def test_send_cta_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.cta123"))

        result = provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="Visit our website",
                display_text="Open Site",
                url="https://example.com",
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.cta123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "cta_url"
        action = payload["interactive"]["action"]
        assert action["name"] == "cta_url"
        assert action["parameters"]["display_text"] == "Open Site"
        assert action["parameters"]["url"] == "https://example.com"

    def test_send_cta_with_header_and_footer(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        result = provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="Click below",
                display_text="Visit",
                url="https://example.com",
                header="Important",
                footer="Terms apply",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["interactive"]["header"]["text"] == "Important"
        assert payload["interactive"]["footer"]["text"] == "Terms apply"

    def test_send_cta_empty_body_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="   ",
                display_text="Click",
                url="https://example.com",
            )
        )
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_cta_no_url_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="Body",
                display_text="Click",
                url="",
            )
        )
        assert not result.succeeded
        assert "No URL" in result.error_message

    def test_send_cta_no_display_text_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="Body",
                display_text="",
                url="https://example.com",
            )
        )
        assert not result.succeeded
        assert "No display text" in result.error_message

    def test_send_cta_truncates_display_text_at_20(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        provider.send(
            WhatsAppInteractiveCTA(
                to="+5511999999999",
                body="Body",
                display_text="D" * 30,
                url="https://example.com",
            )
        )

        payload = mock_client.post.call_args.kwargs["json"]
        display_text = payload["interactive"]["action"]["parameters"]["display_text"]
        assert len(display_text) == 20


class TestSendProduct:
    def test_send_product_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.prod123"))

        result = provider.send(
            WhatsAppProduct(
                to="+5511999999999",
                body="Check out this product",
                catalog_id="CAT001",
                product_retailer_id="SKU001",
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.prod123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "product"
        assert payload["interactive"]["body"]["text"] == "Check out this product"
        assert payload["interactive"]["action"]["catalog_id"] == "CAT001"
        assert payload["interactive"]["action"]["product_retailer_id"] == "SKU001"

    def test_send_product_with_footer(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        result = provider.send(
            WhatsAppProduct(
                to="+5511999999999",
                body="Product info",
                catalog_id="CAT001",
                product_retailer_id="SKU001",
                footer="Limited stock",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["interactive"]["footer"]["text"] == "Limited stock"

    def test_send_product_empty_body_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProduct(
                to="+5511999999999",
                body="   ",
                catalog_id="CAT001",
                product_retailer_id="SKU001",
            )
        )
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_product_no_catalog_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProduct(
                to="+5511999999999",
                body="Body",
                catalog_id="",
                product_retailer_id="SKU001",
            )
        )
        assert not result.succeeded
        assert "No catalog_id" in result.error_message

    def test_send_product_no_product_id_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProduct(
                to="+5511999999999",
                body="Body",
                catalog_id="CAT001",
                product_retailer_id="",
            )
        )
        assert not result.succeeded
        assert "No product_retailer_id" in result.error_message


class TestSendProductList:
    def test_send_product_list_success(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.plist123"))

        sections = [
            {
                "title": "Category",
                "product_items": [
                    {"product_retailer_id": "SKU001"},
                    {"product_retailer_id": "SKU002"},
                ],
            }
        ]
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Browse our products",
                header="Our Catalog",
                catalog_id="CAT001",
                sections=sections,
            )
        )

        assert result.succeeded
        assert result.status == DeliveryStatus.SENT
        assert result.external_id == "wamid.plist123"

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "product_list"
        assert payload["interactive"]["header"]["text"] == "Our Catalog"
        assert payload["interactive"]["body"]["text"] == "Browse our products"
        assert payload["interactive"]["action"]["catalog_id"] == "CAT001"
        action_sections = payload["interactive"]["action"]["sections"]
        assert len(action_sections) == 1
        assert action_sections[0]["title"] == "Category"
        assert len(action_sections[0]["product_items"]) == 2
        assert action_sections[0]["product_items"][0]["product_retailer_id"] == "SKU001"

    def test_send_product_list_with_footer(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response("wamid.xxx"))

        sections = [{"title": "Cat", "product_items": [{"product_retailer_id": "SKU001"}]}]
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Products",
                header="Shop",
                catalog_id="CAT001",
                sections=sections,
                footer="Free shipping",
            )
        )

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["interactive"]["footer"]["text"] == "Free shipping"

    def test_send_product_list_empty_body_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="   ",
                header="Shop",
                catalog_id="CAT001",
                sections=[{"title": "C", "product_items": [{"product_retailer_id": "SKU"}]}],
            )
        )
        assert not result.succeeded
        assert "No message body" in result.error_message

    def test_send_product_list_no_header_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="",
                catalog_id="CAT001",
                sections=[{"title": "C", "product_items": [{"product_retailer_id": "SKU"}]}],
            )
        )
        assert not result.succeeded
        assert "No header" in result.error_message

    def test_send_product_list_no_catalog_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="Shop",
                catalog_id="",
                sections=[{"title": "C", "product_items": [{"product_retailer_id": "SKU"}]}],
            )
        )
        assert not result.succeeded
        assert "No catalog_id" in result.error_message

    def test_send_product_list_no_sections_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="Shop",
                catalog_id="CAT001",
                sections=[],
            )
        )
        assert not result.succeeded
        assert "No sections" in result.error_message

    def test_send_product_list_no_products_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="Shop",
                catalog_id="CAT001",
                sections=[{"title": "Empty", "product_items": []}],
            )
        )
        assert not result.succeeded
        assert "No products" in result.error_message

    def test_send_product_list_too_many_products_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        items = [{"product_retailer_id": f"SKU{i:03d}"} for i in range(31)]
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="Shop",
                catalog_id="CAT001",
                sections=[{"title": "Big", "product_items": items}],
            )
        )
        assert not result.succeeded
        assert "Too many products" in result.error_message

    def test_send_product_list_too_many_sections_fails(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        sections = [{"title": f"Section {i}", "product_items": [{"product_retailer_id": f"SKU{i}"}]} for i in range(11)]
        result = provider.send(
            WhatsAppProductList(
                to="+5511999999999",
                body="Body",
                header="Shop",
                catalog_id="CAT001",
                sections=sections,
            )
        )
        assert not result.succeeded
        assert "Too many sections" in result.error_message


class TestErrorHandling:
    def test_meta_api_error_response(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, _ = _make_provider(
            meta_whatsapp_config,
            _error_response(131030, "Recipient phone number not in allowed list"),
        )

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert result.status == DeliveryStatus.FAILED
        assert result.error_code == "131030"
        assert "not in allowed list" in result.error_message

    def test_network_error(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        mock_client = MagicMock()
        mock_client.post = MagicMock(side_effect=ConnectionError("timeout"))
        provider._client = mock_client

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "timeout" in result.error_message


class TestFetchStatus:
    def test_returns_none(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        assert provider.fetch_status("wamid.xxx") is None


class TestMetaWhatsAppContextManager:
    def test_context_manager_calls_close(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        provider.close = MagicMock()
        with provider:
            pass
        provider.close.assert_called_once()

    async def test_async_context_manager_calls_close(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider = MetaWhatsAppProvider(meta_whatsapp_config)
        provider.close = MagicMock()
        async with provider:
            pass
        provider.close.assert_called_once()


class TestMetaWhatsAppSendAsync:
    async def test_send_async_returns_result(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, _ = _make_provider(meta_whatsapp_config, _ok_response("wamid.async1"))
        result = await provider.send_async(WhatsAppText(to="+5511999999999", body="Hello async"))
        assert result.succeeded
        assert result.external_id == "wamid.async1"


class TestResponseValidation:
    def test_malformed_success_response_fails_gracefully(self, meta_whatsapp_config: MetaWhatsAppConfig):
        """If Meta returns an unexpected response shape, the provider fails gracefully."""
        provider, mock_client = _make_provider(meta_whatsapp_config, MagicMock())
        # Response missing required 'contacts' and 'messages' fields
        mock_client.post.return_value.json.return_value = {"messaging_product": "whatsapp"}

        result = provider.send(WhatsAppText(to="+5511999999999", body="Hello"))

        assert not result.succeeded
        assert "Invalid Meta API response" in result.error_message


class TestBsuidSupport:
    def test_send_text_with_bsuid(self, meta_whatsapp_config: MetaWhatsAppConfig):
        """BSUIDs are passed through to the Meta API unchanged."""
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(WhatsAppText(to="BR.1A2B3C4D5E6F", body="Hello"))

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "BR.1A2B3C4D5E6F"

    def test_send_text_with_whatsapp_prefixed_bsuid(self, meta_whatsapp_config: MetaWhatsAppConfig):
        provider, mock_client = _make_provider(meta_whatsapp_config, _ok_response())

        result = provider.send(WhatsAppText(to="whatsapp:BR.1A2B3C4D5E6F", body="Hello"))

        assert result.succeeded
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["to"] == "BR.1A2B3C4D5E6F"
