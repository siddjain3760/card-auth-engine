"""Tests for slice 1: card validation.

Run from the project root:  python3 -m unittest discover -s tests -v
"""

import unittest
from datetime import date

from app.cards import CardValidation, detect_brand, luhn_check, validate_card


class TestLuhn(unittest.TestCase):
    def test_known_good_visa_passes(self):
        self.assertTrue(luhn_check("4242424242424242"))

    def test_one_digit_off_fails(self):
        self.assertFalse(luhn_check("4242424242424241"))


class TestValidateCard(unittest.TestCase):
    def test_valid_visa(self):
        result = validate_card("4242424242424242", "12/99")
        self.assertTrue(result.valid)
        self.assertEqual(result.brand, "Visa")
        self.assertEqual(result.bin, "42424242")
        self.assertEqual(result.last4, "4242")
        self.assertEqual(result.errors, [])

    def test_spaces_and_dashes_accepted(self):
        self.assertTrue(validate_card("4242 4242 4242 4242", "12/99").valid)
        self.assertTrue(validate_card("4242-4242-4242-4242", "12/99").valid)

    def test_letters_rejected(self):
        result = validate_card("4242 4242 4242 424X", "12/99")
        self.assertFalse(result.valid)
        self.assertIn("only digits", result.errors[0])

    def test_amex_brand_and_length(self):
        result = validate_card("378282246310005", "12/99")
        self.assertTrue(result.valid)
        self.assertEqual(result.brand, "Amex")

    def test_unknown_brand_still_valid(self):
        # 6011... is the well-known Discover test number; we don't map it.
        result = validate_card("6011111111111117", "12/99")
        self.assertTrue(result.valid)
        self.assertEqual(result.brand, "Unknown")

    def test_too_short_and_too_long(self):
        self.assertFalse(validate_card("424242424242", "12/99").valid)  # 12 digits
        self.assertFalse(validate_card("42424242424242424242", "12/99").valid)  # 20 digits

    def test_expired_card(self):
        result = validate_card("4242424242424242", "01/20")
        self.assertFalse(result.valid)
        self.assertIn("expired", result.errors[0])

    def test_expiry_month_itself_still_valid(self):
        # A card expiring this month works until the month ends.
        today = date(2026, 11, 3)
        result = validate_card("4242424242424242", "11/26", today=today)
        self.assertTrue(result.valid)

    def test_bad_month_rejected(self):
        self.assertFalse(validate_card("4242424242424242", "13/30").valid)
        self.assertFalse(validate_card("4242424242424242", "00/30").valid)

    def test_multiple_errors_reported_together(self):
        result = validate_card("4242424242424241", "01/20")
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 2)  # bad checksum AND expired


class TestBrand(unittest.TestCase):
    def test_mastercard_range(self):
        self.assertEqual(detect_brand("5555555555554444"), "Mastercard")


if __name__ == "__main__":
    unittest.main()
