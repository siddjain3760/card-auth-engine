"""Card validation: the first gate of any authorization.

Before a network routes an authorization request to an issuing bank, it
checks that the card itself is well-formed. This module does four things:

1. Normalize: strip spaces and dashes, reject anything else.
2. Luhn check: the checksum digit test every real card number passes.
3. Expiry check: a card is valid through the END of its expiry month.
4. BIN + brand: read the Bank Identification Number (the first 6-8 digits
   of the card), which identifies the issuing bank and card brand.

Design note: validate_card() never raises for bad input. It collects
every problem into `errors` and returns valid=False, so the caller (later,
the authorization engine) can report all problems at once instead of
failing on the first one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class CardValidation:
    """The result of validating one card."""

    valid: bool
    bin: str = ""
    brand: str = "Unknown"
    last4: str = ""
    errors: list[str] = field(default_factory=list)


def normalize(number: str) -> str:
    """Strip spaces and dashes; reject any other non-digit character."""
    cleaned = number.replace(" ", "").replace("-", "")
    if not cleaned.isdigit():
        raise ValueError("card number must contain only digits, spaces, and dashes")
    return cleaned


def luhn_check(digits: str) -> bool:
    """Return True if the number passes the Luhn checksum.

    Walk from the rightmost digit, doubling every second digit (and
    subtracting 9 when a doubled digit exceeds 9). If the total is a
    multiple of 10, the number is well-formed. This catches typos, not
    fraud: a made-up number can still pass Luhn.
    """
    total = 0
    for i, char in enumerate(reversed(digits)):
        digit = int(char)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def detect_brand(digits: str) -> str:
    """Guess the brand from the leading digits (the BIN range)."""
    if digits.startswith("4"):
        return "Visa"
    if digits[:2] in ("51", "52", "53", "54", "55"):
        return "Mastercard"
    if digits[:2] in ("34", "37"):
        return "Amex"
    return "Unknown"


def parse_expiry(expiry: str) -> tuple[int, int]:
    """Parse "MM/YY" into (month, full year). Raises ValueError if bad."""
    parts = expiry.split("/")
    if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
        raise ValueError('expiry must look like "MM/YY", e.g. "09/28"')
    month, year = int(parts[0]), 2000 + int(parts[1])
    if not 1 <= month <= 12:
        raise ValueError("expiry month must be between 01 and 12")
    return month, year


def validate_card(number: str, expiry: str, today: date | None = None) -> CardValidation:
    """Validate a card number + expiry. Never raises for bad input."""
    today = today or date.today()
    errors: list[str] = []
    digits = ""
    try:
        digits = normalize(number)
    except ValueError as exc:
        errors.append(str(exc))

    if digits:
        if not 13 <= len(digits) <= 19:
            errors.append("card number must be 13 to 19 digits long")
        elif not luhn_check(digits):
            errors.append("card number fails the Luhn checksum")

    try:
        month, year = parse_expiry(expiry)
        # A card is valid through the END of its expiry month, so it only
        # counts as expired once a strictly later month begins.
        if (year, month) < (today.year, today.month):
            errors.append("card is expired")
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        return CardValidation(valid=False, errors=errors)
    return CardValidation(
        valid=True,
        bin=digits[:8],
        brand=detect_brand(digits),
        last4=digits[-4:],
    )
