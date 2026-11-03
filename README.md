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

- **Slice 1 (this commit): card validation** — normalize the number,
  Luhn checksum, expiry check, BIN + brand detection. No API yet.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

No dependencies for slice 1 — standard library only.
