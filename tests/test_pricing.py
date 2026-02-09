"""Tests for pricing calculation."""

from decimal import Decimal

from messaging.pricing import calculate_template_cost


class TestPricing:
    def test_marketing(self):
        assert calculate_template_cost("MARKETING") == Decimal("0.0600")

    def test_utility(self):
        assert calculate_template_cost("UTILITY") == Decimal("0.0200")

    def test_authentication(self):
        assert calculate_template_cost("AUTHENTICATION") == Decimal("0.0150")

    def test_none_defaults_to_utility(self):
        assert calculate_template_cost(None) == Decimal("0.0200")

    def test_case_insensitive(self):
        assert calculate_template_cost("marketing") == Decimal("0.0600")
        assert calculate_template_cost("Marketing") == Decimal("0.0600")

    def test_unknown_defaults_to_utility(self):
        assert calculate_template_cost("UNKNOWN") == Decimal("0.0200")
