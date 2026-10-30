# The transaction feed

The card processor sends every transaction as a record with an `external_id`. It resends a record
whenever something about the transaction changes: the merchant's name is cleaned up, the amount is
corrected after a partial capture, the posting time is settled, or it moves from `pending` to
`posted`. Each resend carries the same `external_id` and a higher `version`.

`TxnStore.add` keeps every version we receive (compliance wants the history). The latest version
of each transaction is the truth; older versions are history only. `TxnStore.current()` returns
just the latest versions.

All `posted_at` times are timezone-aware UTC datetimes.
