# card-auth-engine

A card authorization + clearing + settlement engine, modeled on how card
networks (like Visa) actually move money. Built in small slices, each one
reviewed before the next is built.

## The lifecycle (what this project models)

1. **Authorization** — a merchant asks "is this card good for this amount?"
   The network validates the card, screens for fraud, and approves or
   declines with a reason code.
2. **Clearing** — approved transactions are batched into a file so every
   bank knows what it owes whom.
3. **Settlement** — actual money moves between banks based on that file.

## Slices

- **Slice 1: card validation** — normalize the number,
  Luhn checksum, expiry check, BIN + brand detection. No API yet.
- **Slice 2: fraud rules** — velocity, amount-spike, blocked-category,
  and country checks as pure functions, plus a run_all_rules helper that
  returns the first triggered reason code. Still no API or database.

## Slice 2: fraud rules, with examples

After a card passes validation, each purchase is screened before any
approve/decline decision:

- **Velocity:** 5 prior attempts in the last 10 minutes → decline with
  reason VELOCITY. A thief testing a stolen card tries many times fast;
  a real shopper doesn't.
- **Amount spike:** past purchases average $20, this one is $100+ (more
  than 5x the average) → AMOUNT_SPIKE. With no purchase history, the
  rule stays quiet — nothing to compare against.
- **Blocked category:** the merchant's category code (MCC) is on the
  issuer's blocklist, e.g. 7995 for betting → BLOCKED_CATEGORY.
- **Country:** first purchase ever from a country the card hasn't been
  used in → SUSPICIOUS_COUNTRY. A signal, not proof — people travel.

Rules run in that order and the first one that fires wins, so every
decline carries exactly one explainable reason.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

No dependencies for slice 1 — standard library only.
