"""Tests for slice 2: fraud rules.

Run from the project root:  python3 -m unittest discover -s tests -v
"""

import unittest
from datetime import datetime, timedelta

from app.fraud import (
    Attempt,
    check_amount_spike,
    check_blocked_category,
    check_country,
    check_velocity,
    run_all_rules,
)

NOW = datetime(2026, 11, 4, 12, 0, 0)


def minutes_ago(n: int) -> datetime:
    return NOW - timedelta(minutes=n)


class TestVelocity(unittest.TestCase):
    def test_five_priors_in_window_triggers(self):
        priors = [minutes_ago(m) for m in (1, 3, 5, 7, 9)]
        verdict = check_velocity(priors, NOW)
        self.assertTrue(verdict.triggered)
        self.assertEqual(verdict.reason, "VELOCITY")

    def test_four_priors_is_clean(self):
        priors = [minutes_ago(m) for m in (1, 3, 5, 7)]
        self.assertFalse(check_velocity(priors, NOW).triggered)

    def test_old_priors_do_not_count(self):
        priors = [minutes_ago(m) for m in (30, 45, 60, 90, 120)]
        self.assertFalse(check_velocity(priors, NOW).triggered)

    def test_boundary_exactly_window_old_counts(self):
        priors = [minutes_ago(10), minutes_ago(2), minutes_ago(3), minutes_ago(4), minutes_ago(5)]
        self.assertTrue(check_velocity(priors, NOW).triggered)

    def test_boundary_one_second_older_does_not_count(self):
        priors = [
            NOW - timedelta(minutes=10, seconds=1),
            minutes_ago(2),
            minutes_ago(3),
            minutes_ago(4),
            minutes_ago(5),
        ]
        self.assertFalse(check_velocity(priors, NOW).triggered)


class TestAmountSpike(unittest.TestCase):
    def test_big_purchase_triggers(self):
        # Past average is 1500 cents; 5x is 7500; 10000 is above it.
        verdict = check_amount_spike(10000, [1000, 2000])
        self.assertTrue(verdict.triggered)
        self.assertEqual(verdict.reason, "AMOUNT_SPIKE")

    def test_normal_purchase_is_clean(self):
        self.assertFalse(check_amount_spike(5000, [1000, 2000]).triggered)

    def test_no_history_stays_quiet(self):
        self.assertFalse(check_amount_spike(100000, []).triggered)


class TestBlockedCategory(unittest.TestCase):
    def test_blocked_mcc_triggers(self):
        verdict = check_blocked_category("7995")
        self.assertTrue(verdict.triggered)
        self.assertEqual(verdict.reason, "BLOCKED_CATEGORY")

    def test_grocery_is_clean(self):
        self.assertFalse(check_blocked_category("5411").triggered)

    def test_custom_blocklist(self):
        self.assertTrue(check_blocked_category("5411", blocked={"5411"}).triggered)


class TestCountry(unittest.TestCase):
    def test_first_seen_country_triggers(self):
        verdict = check_country("FR", {"US"})
        self.assertTrue(verdict.triggered)
        self.assertEqual(verdict.reason, "SUSPICIOUS_COUNTRY")

    def test_usual_country_is_clean(self):
        self.assertFalse(check_country("US", {"US", "CA"}).triggered)

    def test_no_history_stays_quiet(self):
        self.assertFalse(check_country("FR", set()).triggered)


class TestRunAllRules(unittest.TestCase):
    def clean_attempt(self) -> Attempt:
        return Attempt(
            amount_cents=2000,
            mcc="5411",
            country_code="US",
            past_amounts_cents=[1500, 2500],
            usual_countries={"US"},
            prior_attempts=[],
            now=NOW,
        )

    def test_clean_attempt_passes(self):
        self.assertFalse(run_all_rules(self.clean_attempt()).triggered)

    def test_first_match_wins(self):
        # Velocity AND amount spike both fire; velocity is first.
        attempt = self.clean_attempt()
        attempt.prior_attempts = [minutes_ago(m) for m in (1, 2, 3, 4, 5)]
        attempt.amount_cents = 50000
        verdict = run_all_rules(attempt)
        self.assertEqual(verdict.reason, "VELOCITY")

    def test_amount_spike_alone(self):
        attempt = self.clean_attempt()
        attempt.amount_cents = 50000
        verdict = run_all_rules(attempt)
        self.assertEqual(verdict.reason, "AMOUNT_SPIKE")


if __name__ == "__main__":
    unittest.main()
