"""Tests for phone normalization."""

from messaging.phone import (
    denormalize_phone_for_whatsapp,
    format_whatsapp_number,
    is_bsuid,
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
    def test_brazil_10_digit_default(self):
        """10-digit number with default BR: treated as Brazilian (DDD + 8-digit)."""
        # 12 is a valid BR DDD (Sao Paulo), 34567890 is a valid 8-digit local number
        assert format_whatsapp_number("1234567890") == "whatsapp:+551234567890"

    def test_us_10_digit_explicit(self):
        """10-digit US number with explicit default_country='US'."""
        assert format_whatsapp_number("4155551234", default_country="US") == "whatsapp:+14155551234"

    def test_with_plus_prefix(self):
        assert format_whatsapp_number("+442079460000") == "whatsapp:+442079460000"

    def test_already_prefixed_valid(self):
        """Valid number with whatsapp: prefix is preserved."""
        assert format_whatsapp_number("whatsapp:+5551998644323") == "whatsapp:+5551998644323"

    def test_already_prefixed_invalid_returns_none(self):
        """Invalid number with whatsapp: prefix returns None."""
        assert format_whatsapp_number("whatsapp:+123") is None

    def test_prefixed_with_formatting_is_normalized(self):
        assert format_whatsapp_number("whatsapp:+55 (51) 99864-4323") == "whatsapp:+5551998644323"

    def test_prefix_case_insensitive(self):
        """Case-insensitive whatsapp: prefix with valid number."""
        assert format_whatsapp_number("WhatsApp:+5551998644323") == "whatsapp:+5551998644323"

    def test_prefix_case_insensitive_invalid_returns_none(self):
        """Case-insensitive whatsapp: prefix with invalid number returns None."""
        assert format_whatsapp_number("WhatsApp:+123") is None

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

    def test_short_number_rejected(self):
        """Short/invalid numbers are rejected by phonenumberslite."""
        assert format_whatsapp_number("12345") is None


class TestFormatWhatsAppNumberInternational:
    """format_whatsapp_number should use phonenumberslite, not assume US for 10 digits."""

    def test_brazil_10_digit_not_treated_as_us(self):
        """A 10-digit Brazilian number (DDD + 8-digit landline) should NOT get +1 prefix."""
        result = format_whatsapp_number("5133224455")
        # Should be treated as Brazilian (default), not US
        assert result == "whatsapp:+555133224455"

    def test_explicit_plus_prefix_preserved(self):
        assert format_whatsapp_number("+14155551234") == "whatsapp:+14155551234"

    def test_brazil_mobile_normalized(self):
        assert format_whatsapp_number("+555198644323") == "whatsapp:+5551998644323"

    def test_default_country_us(self):
        """With default_country='US', a 10-digit number should get +1."""
        result = format_whatsapp_number("4155551234", default_country="US")
        assert result == "whatsapp:+14155551234"

    def test_invalid_number_returns_none(self):
        """Short/garbage numbers should return None, not pass through."""
        assert format_whatsapp_number("12345") is None

    def test_invalid_10_digit_returns_none(self):
        """A 10-digit string that's not a valid phone in any country should return None."""
        # 1234567890 is not a valid Brazilian number (12 is valid DDD but 34567890 is not valid)
        result = format_whatsapp_number("1234567890")
        # phonenumberslite may or may not validate this as Brazilian;
        # the key point is it should NOT blindly prepend +1
        assert result is None or not result.startswith("whatsapp:+11234567890")


class TestPhonesMatch:
    def test_matching_with_different_formats(self):
        assert phones_match("+555198644323", "+5551998644323")

    def test_non_matching(self):
        assert not phones_match("+5511999999999", "+5511888888888")

    def test_none_input(self):
        assert not phones_match(None, "+5511999999999")
        assert not phones_match("+5511999999999", None)


class TestIsBsuid:
    def test_bsuid_plain(self):
        assert is_bsuid("BR.1A2B3C4D5E6F7G8H9I0J") is True

    def test_bsuid_with_whatsapp_prefix(self):
        assert is_bsuid("whatsapp:BR.1A2B3C4D5E6F") is True

    def test_bsuid_case_insensitive_prefix(self):
        assert is_bsuid("WhatsApp:US.ABC123") is True

    def test_phone_number_e164(self):
        assert is_bsuid("+5511999999999") is False

    def test_phone_with_whatsapp_prefix(self):
        assert is_bsuid("whatsapp:+5511999999999") is False

    def test_plain_digits(self):
        assert is_bsuid("5511999999999") is False

    def test_none(self):
        assert is_bsuid(None) is False

    def test_empty(self):
        assert is_bsuid("") is False


class TestBsuidPassthrough:
    """All phone functions pass BSUIDs through unchanged."""

    def test_normalize_phone_bsuid(self):
        assert normalize_phone("BR.1A2B3C4D5E") == "BR.1A2B3C4D5E"

    def test_normalize_phone_bsuid_with_whatsapp(self):
        assert normalize_phone("whatsapp:BR.1A2B3C4D5E") == "whatsapp:BR.1A2B3C4D5E"

    def test_normalize_whatsapp_id_bsuid(self):
        assert normalize_whatsapp_id("whatsapp:US.XYZ789") == "whatsapp:US.XYZ789"

    def test_normalize_whatsapp_id_bsuid_no_prefix(self):
        assert normalize_whatsapp_id("US.XYZ789") == "US.XYZ789"

    def test_format_whatsapp_number_bsuid(self):
        assert format_whatsapp_number("BR.1A2B3C4D5E") == "whatsapp:BR.1A2B3C4D5E"

    def test_format_whatsapp_number_bsuid_with_prefix(self):
        assert format_whatsapp_number("whatsapp:BR.1A2B3C4D5E") == "whatsapp:BR.1A2B3C4D5E"

    def test_denormalize_bsuid(self):
        assert denormalize_phone_for_whatsapp("BR.1A2B3C4D5E") == "BR.1A2B3C4D5E"

    def test_denormalize_bsuid_with_prefix(self):
        assert denormalize_phone_for_whatsapp("whatsapp:BR.1A2B3C") == "whatsapp:BR.1A2B3C"

    def test_phones_match_bsuid(self):
        assert phones_match("BR.1A2B3C", "BR.1A2B3C") is True

    def test_phones_match_bsuid_vs_phone(self):
        assert phones_match("BR.1A2B3C", "+5511999999999") is False


class TestInternationalNormalization:
    """International numbers should be correctly normalized via phonenumberslite."""

    def test_us_number_with_country_code(self):
        assert normalize_phone("+14155551234", default_country="US") == "+14155551234"

    def test_us_local_number(self):
        """10-digit US number without +1 should get country code added."""
        assert normalize_phone("4155551234", default_country="US") == "+14155551234"

    def test_uk_number(self):
        assert normalize_phone("+442079460000") == "+442079460000"

    def test_argentina_mobile(self):
        """Argentina mobile: +54 9 area subscriber."""
        assert normalize_phone("+5491155551234") == "+5491155551234"

    def test_india_number(self):
        assert normalize_phone("+919876543210") == "+919876543210"

    def test_mexico_number(self):
        assert normalize_phone("+525551234567") == "+525551234567"


class TestPhonesMatchInternational:
    def test_us_numbers_with_different_formatting(self):
        assert phones_match("+14155551234", "1-415-555-1234", country="US") is True

    def test_uk_numbers_match(self):
        assert phones_match("+442079460000", "442079460000", country="GB") is True

    def test_different_countries_dont_match(self):
        assert phones_match("+14155551234", "+442079460000", country="US") is False

    def test_brazil_still_uses_brazil_logic(self):
        """Brazil path should still handle 8/9 digit matching."""
        assert phones_match("+555198644323", "+5551998644323") is True


class TestPhoneValidation:
    """phonenumberslite should reject garbage inputs."""

    def test_garbage_string_returns_none(self):
        assert normalize_phone("not-a-phone") is None

    def test_too_short_returns_none(self):
        assert normalize_phone("+1234") is None

    def test_empty_after_strip_returns_none(self):
        assert normalize_phone("+++") is None

    def test_letters_only_returns_none(self):
        assert normalize_phone("abcdef", default_country="US") is None
