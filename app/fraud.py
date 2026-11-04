"""Fraud rules: the screening layer between validation and decision.

Slice 1 answered "is this card well-formed?" These rules answer the next
question: "does this purchase look like fraud?" Each rule is a pure
function: it takes inputs, returns a verdict, and touches nothing else
(no database, no network). That makes rules easy to test, easy to reason
about, and easy to explain when a decline is questioned.

Every rule returns a FraudVerdict. When a rule fires, its `reason` is a
short code (VELOCITY, AMOUNT_SPIKE, BLOCKED_CATEGORY, SUSPICIOUS_COUNTRY)
so a decline always explains itself. When nothing fires, triggered is
False and the purchase is clean as far as these rules can tell.

run_all_rules() runs the rules in a fixed order and returns the FIRST
rule that fires. One clear reason per decline keeps decisions
explainable: "declined for velocity" is actionable, "declined for five
reasons" is not.

These rules are deliberately simple. Real fraud systems add machine
learning models, device fingerprints, and behavioral history on top —
but rule engines like this one still sit underneath, because a rule's
decision can always be explained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class FraudVerdict:
    """The outcome of one fraud rule (or of all rules together)."""

    triggered: bool
    reason: str = ""
    detail: str = ""


@dataclass
class Attempt:
    """Everything the rules need to judge one purchase attempt."""

    amount_cents: int
    mcc: str
    country_code: str
    past_amounts_cents: list[int] = field(default_factory=list)
    usual_countries: set[str] = field(default_factory=set)
    prior_attempts: list[datetime] = field(default_factory=list)
    now: datetime | None = None


def check_velocity(
    prior_attempts: list[datetime],
    now: datetime | None = None,
    max_attempts: int = 5,
    window_minutes: int = 10,
) -> FraudVerdict:
    """Flag when too many attempts happened inside a short window.

    Thieves test a stolen card with many quick attempts. If max_attempts
    prior attempts fall inside the window, this attempt is one too many.
    An attempt exactly window_minutes old still counts; anything older
    does not. Boundary choices like this must be written down, because
    two engineers will otherwise implement them differently.
    """
    now = now or datetime.now()
    window_start = now - timedelta(minutes=window_minutes)
    recent = [t for t in prior_attempts if window_start <= t <= now]
    if len(recent) >= max_attempts:
        return FraudVerdict(
            True, "VELOCITY", f"{len(recent)} attempts in the last {window_minutes} minutes"
        )
    return FraudVerdict(False)


def check_amount_spike(
    amount_cents: int,
    past_amounts_cents: list[int],
    multiple: int = 5,
) -> FraudVerdict:
    """Flag a purchase far above the card's usual spending.

    With no history there is nothing to compare against, so the rule
    stays quiet. Otherwise: amount > multiple * average past amount
    triggers. Real systems also add a minimum-amount floor so tiny
    purchases can't trip the rule; this slice keeps the one knob.
    """
    if not past_amounts_cents:
        return FraudVerdict(False)
    average = sum(past_amounts_cents) / len(past_amounts_cents)
    if amount_cents > multiple * average:
        return FraudVerdict(
            True, "AMOUNT_SPIKE", f"{amount_cents} cents vs {average:.0f} average"
        )
    return FraudVerdict(False)


# Example blocklist: betting/gambling and tobacco. Issuers configure
# their own lists; these are just recognizable examples.
DEFAULT_BLOCKED_MCCS = {"7995", "5993"}


def check_blocked_category(
    mcc: str,
    blocked: set[str] = DEFAULT_BLOCKED_MCCS,
) -> FraudVerdict:
    """Flag a purchase in a merchant category the issuer blocks."""
    if mcc in blocked:
        return FraudVerdict(True, "BLOCKED_CATEGORY", f"MCC {mcc} is blocked")
    return FraudVerdict(False)


def check_country(country_code: str, usual_countries: set[str]) -> FraudVerdict:
    """Flag a purchase from a country the card has never been used in.

    A first-seen country is a signal, not proof: people travel. Real
    systems combine it with risk lists and travel notices. With no
    history at all, the rule stays quiet.
    """
    if not usual_countries:
        return FraudVerdict(False)
    if country_code not in usual_countries:
        return FraudVerdict(
            True, "SUSPICIOUS_COUNTRY", f"first purchase from {country_code}"
        )
    return FraudVerdict(False)


def run_all_rules(attempt: Attempt) -> FraudVerdict:
    """Run every rule in order; return the first verdict that fires."""
    now = attempt.now or datetime.now()
    checks = [
        check_velocity(attempt.prior_attempts, now),
        check_amount_spike(attempt.amount_cents, attempt.past_amounts_cents),
        check_blocked_category(attempt.mcc),
        check_country(attempt.country_code, attempt.usual_countries),
    ]
    for verdict in checks:
        if verdict.triggered:
            return verdict
    return FraudVerdict(False)
