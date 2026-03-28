"""Tests for Telegram Bot API Pydantic schemas."""

import pytest
from pydantic import ValidationError

from messaging.telegram.schemas import (
    TelegramErrorResponse,
    TelegramMediaPayload,
    TelegramSuccessResponse,
    TelegramTextPayload,
)


class TestTelegramTextPayload:
    def test_serializes_with_int_chat_id(self):
        msg = TelegramTextPayload(chat_id=12345, text="Hello")
        payload = msg.model_dump(exclude_none=True)
        assert payload == {"chat_id": 12345, "text": "Hello"}

    def test_serializes_with_string_chat_id(self):
        msg = TelegramTextPayload(chat_id="@mychannel", text="Post")
        payload = msg.model_dump(exclude_none=True)
        assert payload == {"chat_id": "@mychannel", "text": "Post"}

    def test_includes_parse_mode_when_set(self):
        msg = TelegramTextPayload(chat_id=1, text="<b>Bold</b>", parse_mode="HTML")
        payload = msg.model_dump(exclude_none=True)
        assert payload["parse_mode"] == "HTML"

    def test_excludes_parse_mode_when_none(self):
        msg = TelegramTextPayload(chat_id=1, text="plain")
        payload = msg.model_dump(exclude_none=True)
        assert "parse_mode" not in payload


class TestTelegramMediaPayload:
    def test_photo_excludes_other_media_fields(self):
        msg = TelegramMediaPayload(
            chat_id=12345,
            photo="https://example.com/photo.jpg",
            caption="Look!",
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["photo"] == "https://example.com/photo.jpg"
        assert payload["caption"] == "Look!"
        assert "document" not in payload
        assert "video" not in payload

    def test_document_without_caption(self):
        msg = TelegramMediaPayload(
            chat_id=12345,
            document="https://example.com/file.pdf",
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["document"] == "https://example.com/file.pdf"
        assert "caption" not in payload
        assert "photo" not in payload

    def test_video_with_parse_mode(self):
        msg = TelegramMediaPayload(
            chat_id=12345,
            video="https://example.com/clip.mp4",
            caption="<b>Watch</b>",
            parse_mode="HTML",
        )
        payload = msg.model_dump(exclude_none=True)
        assert payload["video"] == "https://example.com/clip.mp4"
        assert payload["parse_mode"] == "HTML"


class TestTelegramResponseModels:
    def test_success_response_parses(self):
        data = {"ok": True, "result": {"message_id": 42}}
        resp = TelegramSuccessResponse.model_validate(data)
        assert resp.ok is True
        assert resp.result.message_id == 42

    def test_error_response_parses(self):
        data = {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked"}
        resp = TelegramErrorResponse.model_validate(data)
        assert resp.error_code == 403
        assert resp.description == "Forbidden: bot was blocked"

    def test_success_response_rejects_missing_result(self):
        with pytest.raises(ValidationError):
            TelegramSuccessResponse.model_validate({"ok": True})

    def test_error_response_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            TelegramErrorResponse.model_validate({"ok": False})
