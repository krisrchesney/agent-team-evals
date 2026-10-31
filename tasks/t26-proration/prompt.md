Customers on 28-day and 31-day cycles say our mid-cycle charges don't add up, because `billkit` prorates as if every month had 30 days. Prorate by the real length of the billing period instead: a February cycle has 28 or 29 days, a yearly plan 365 or 366.

This has to hold everywhere `billkit` prorates, not only in the paths you happen to notice first. Only the length of the period changes: each place keeps the rounding it has today, and nothing that merely uses the number 30 for something else should change.

Existing behaviour must keep working. Use only the Python standard library. Existing tests are in `tests/`.
