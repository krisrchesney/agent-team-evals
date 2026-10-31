# t32-soft-delete: where each hidden-test rule is shown

Category `cross-module`: the prompt lists twelve numbered requirements and the hidden tests (named
`test_r<N>_...`) walk every path that reads, counts, lists, searches, exports or saves rows. Every
rule is in the prompt. This file is outside `repo/`, so agents never see it.

Nine hidden tests already pass on the starting repo (`test_r1_a_deleted_*_is_not_found`,
`test_r1_one_event_per_delete_with_the_old_data`, `test_r4_*` two of three, `test_r5_lists`,
`test_r5_counts_in_views`, `test_r5_exports`): they check that a deleted row is invisible, which hard
delete already satisfies. They are the "nothing may leak back in" half of the task.

| Test(s) | Rule | Shown by |
|---|---|---|
| `test_r1_*` (6 tests) | delete returns the view with `deleted_at`; deleted rows are `NotFound` with the usual `param` through every entry point; one event with the old data | prompt 1; `customers.py`, `tickets.py`, `comments.py`, `store.py` lookups |
| `test_r2_*` (3 tests) | cascade to live children; earlier deletes keep their time; children share the parent's time | prompt 2; the cascade in `customers.delete` / `tickets.delete` |
| `test_r3_*` (8 tests) | restore returns only what went with it; the three Conflict cases and their `param`; a failed restore changes nothing; events | prompt 3 |
| `test_r4_*` (3 tests) | email unique among live customers; index follows delete and restore | prompt 4; `store._email`, `customers.create/update/find_by_email` |
| `test_r5_*` (9 tests) | lists, view counts, search scores (index rebuilt without deleted text), all six reports, exports, `stats.deleted` | prompt 5; `tickets.list_`, `views.py`, `search.py`, `reports.py`, `exporter.py` (these read `store.tickets` / `store.customers` directly) |
| `test_r6_*` (3 tests) | `include_deleted` on the listed calls, CSV `deleted_at` column | prompt 6 |
| `test_r7_*` (2 tests) | merge moves deleted tickets too, only `customer.merged` is recorded | prompt 7; `customers.merge` |
| `test_r8_*` (2 tests) | rename reaches deleted tickets, counts live ones | prompt 8; `tickets.rename_tag` |
| `test_r9_*` (5 tests) | feed unfiltered; trash order, label, filter, limit | prompt 9; `activity.py` |
| `test_r10_*` (6 tests) | purge rules, cascade, errors, indexes stay intact, ids not reused | prompt 10; `ids.py` counters |
| `test_r11_*` (5 tests) | 30-day retention boundary, counts, one event, old rows under a newer delete go alone | prompt 11 |
| `test_r12_*` (4 tests) | dump keeps deleted rows and what restore needs; email index and ids survive; older dump | prompt 12; `snapshot.py` |

What makes it hard: soft delete is one idea, but the starting code has about ten places that read the
tables without going through a lookup that could be changed in one spot: `tickets.list_`,
`customers.list_`, the five reports, the two CSV exports, the search index (built from the store),
the email and tag indexes, `merge`, `rename_tag`, `stats` and `snapshot`. Missing one fails a test.
The cascade needs a way to tell "deleted together with the parent" from "deleted earlier on its
own" (the solution stores `deleted_with`; the prompt only states the behaviour), and restore has
to put the search index back in the right order.
