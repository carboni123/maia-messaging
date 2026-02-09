"""Tests for phone normalization."""

from messaging.phone import (
    denormalize_phone_for_whatsapp,
    format_whatsapp_number,
    normalize_phone,
    normalize_whatsapp_id,
    phones_match,
)
from messaging.phone.brazil import denormalize_brazil_phone, normalize_brazil_phone


class TestBrazilNormalize:
    def test_adds_9th_digit(self):
        assert normalize_brazil_phone("+555198644323") == "+5551998644323"

    def test_already_has_9th_digit(self):
        assert normalize_brazil_phone("+5551998644323") == "+5551998644323"

    def test_local_format(self):
        assert normalize_brazil_phone("5198644323") == "+5551998644323"

    def test_whatsapp_prefix(self):
        assert normalize_brazil_phone("whatsapp:+555198644323") == "whatsapp:+5551998644323"

    def test_landline_unchanged(self):
        assert normalize_brazil_phone("+555133224455") == "+555133224455"

    def test_none_input(self):
        assert normalize_brazil_phone(None) is None

    def test_empty_input(self):
        assert normalize_brazil_phone("") is None
        assert normalize_brazil_phone("  ") is None

    def test_invalid_short_number(self):
        assert normalize_brazil_phone("123") is None


class TestBrazilDenormalize:
    def test_removes_9th_digit(self):
        assert denormalize_brazil_phone("+5551998644323") == "+555198644323"

    def test_landline_unchanged(self):
        assert denormalize_brazil_phone("+555133224455") == "+555133224455"

    def test_whatsapp_prefix(self):
        assert denormalize_brazil_phone("whatsapp:+5551998644323") == "whatsapp:+555198644323"

    def test_none_input(self):
        assert denormalize_brazil_phone(None) is None

    def test_non_brazilian(self):
        assert denormalize_brazil_phone("+14155238886") == "+14155238886"


class TestNormalizePhone:
    def test_brazil_default(self):
        assert normalize_phone("+555198644323") == "+5551998644323"

    def test_international_plus_number_not_rewritten_to_brazil(self):
        assert normalize_phone("+14155551234") == "+14155551234"

    def test_international_plus_number_with_formatting(self):
        assert normalize_phone("+1 (415) 555-1234") == "+14155551234"

    def test_generic_number(self):
        assert normalize_phone("+14155238886", default_country="US") == "+14155238886"

    def test_adds_plus_prefix(self):
        assert normalize_phone("14155238886", default_country="US") == "+14155238886"

    def test_none_input(self):
        assert normalize_phone(None) is None


class TestNormalizeWhatsAppId:
    def test_with_prefix(self):
        assert normalize_whatsapp_id("whatsapp:+555198644323") == "whatsapp:+5551998644323"

    def test_without_prefix(self):
        assert normalize_whatsapp_id("+555198644323") == "+5551998644323"

    def test_non_brazil_prefix_is_preserved(self):
        assert normalize_whatsapp_id("whatsapp:+14155551234") == "whatsapp:+14155551234"

    def test_none(self):
        assert normalize_whatsapp_id(None) is None


class TestDenormalizeForWhatsApp:
    def test_brazil(self):
        assert denormalize_phone_for_whatsapp("+5551998644323") == "+555198644323"

    def test_non_brazil(self):
        assert denormalize_phone_for_whatsapp("+14155238886", country="US") == "+14155238886"

    def test_none(self):
        assert denormalize_phone_for_whatsapp(None) is None


class TestFormatWhatsAppNumber:
    def test_us_10_digit(self):
        assert format_whatsapp_number("1234567890") == "whatsapp:+11234567890"

    def test_with_plus_prefix(self):
        assert format_whatsapp_number("+442079460000") == "whatsapp:+442079460000"

    def test_already_prefixed(self):
        assert format_whatsapp_number("whatsapp:+123") == "whatsapp:+123"

    def test_prefixed_with_formatting_is_normalized(self):
        assert format_whatsapp_number("whatsapp:+55 (51) 99864-4323") == "whatsapp:+5551998644323"

    def test_prefix_case_insensitive(self):
        assert format_whatsapp_number("WhatsApp:+123") == "whatsapp:+123"

    def test_none_input(self):
        assert format_whatsapp_number(None) is None

    def test_empty_string(self):
        assert format_whatsapp_number("") is None
        assert format_whatsapp_number("   ") is None

    def test_non_digit_characters_stripped(self):
        assert format_whatsapp_number("+55 (51) 99864-4323") == "whatsapp:+5551998644323"

    def test_all_non_digit(self):
        assert format_whatsapp_number("abc") is None

    def test_brazil_number(self):
        assert format_whatsapp_number("+5551998644323") == "whatsapp:+5551998644323"

    def test_short_number_not_padded(self):
        """Numbers with fewer than 10 digits are used as-is (not US-assumed)."""
        assert format_whatsapp_number("12345") == "whatsapp:+12345"


class TestPhonesMatch:
    def test_matching_with_different_formats(self):
        assert phones_match("+555198644323", "+5551998644323")

    def test_non_matching(self):
        assert not phones_match("+5511999999999", "+5511888888888")

    def test_none_input(self):
        assert not phones_match(None, "+5511999999999")
        assert not phones_match("+5511999999999", None)
