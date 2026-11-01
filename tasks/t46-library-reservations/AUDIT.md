# t46-library-reservations: where each hidden-test rule is shown

The repo has no docs folder. The prompt names the operations, the statuses, `pickup_by`, the 3 days and
the queue rule. Everything else is shown by the existing code. This file is outside `repo/`, so agents
never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_operations_are_registered` | operations registered by name; the module must be imported | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_reservation_view`, `test_ids_are_sequential` | id from `svc.ids.new("reservation")`: the prefix is the full noun; `created_at`/`updated_at`/`version` 1; timestamps via `stamp()`; `pickup_by` is null until ready | `ops/members.py` (`member`), `ops/books.py` (`book`), `loans.py` (`loan`, `fine`); `views.py` (book, member and loan views all carry the three fields; `returned_at` is None until set); prompt (`pickup_by`) |
| `test_create_event_carries_the_returned_view`, `test_*_event*` | one event per mutated record; `create` ops emit `<noun>.created`; a status change emits `<noun>.<new status>` (`reservation.ready`, `.fulfilled`, `.cancelled`); data `{"<noun>": view}` equal to the view that is returned or retrievable | `member.create`, `book.create`, `loan.checkout` (`created`); `loan.returned`, `member.suspended`, `book.retired` (the event suffix is the new status value); every op emits `{noun: view}` |
| `test_ids_are_given_to_extra_records_only_after_validation`, `test_book_is_checked_before_member`, `test_failures_change_nothing`, `test_cancel_conflicts_change_nothing` | getters first (`get_book`, then `get_member`), then state checks, ids and changes last; no event on failure | `loan.checkout` (book, member, then conflicts, then `ids.new`), `loan.return` |
| `test_ids_are_read_like_other_strings` | arguments are read with `validate.require_str` (stripped, `InvalidRequest` with `param`) | every op |
| `test_a_book_with_a_free_copy_cannot_be_reserved` | prompt rule, `Conflict` | prompt ("Only a book with no copy available can be reserved") |
| `test_a_suspended_member_cannot_reserve` | `Conflict`, `param="member"` | `loan.checkout` |
| `test_a_retired_book_cannot_be_reserved` | `Conflict` (class only: a retired book also has a free copy) | `loan.checkout` |
| `test_a_member_cannot_wait_twice_or_reserve_what_they_hold` | duplicates are a `Conflict` (class only) | `errors.Conflict`; `loan.return` already-returned |
| `test_unknown_reservation` | a getter like `get_loan` raising `NotFound` with `param` = argument name | `store.get_loan`; `loan.retrieve` |
| `test_return_makes_the_first_in_line_ready` | first in line = lowest id (ids are in placement order); `pickup_by` = now + 3 days; `store.bump` | prompt; `Store.open_loans` ("oldest id first"); every mutating op bumps |
| `test_events_of_a_return_come_in_order`, `test_late_return_...` | the operation's own event first, then those for what it caused, built by `loans.close` and emitted in one loop | `loan.return` + `loans.close` (`loan.returned`, then `fine.charged`) |
| `test_checkout_events_come_in_order`, `test_cancel...passes_the_copy_on` | the same rule for checkout (`loan.created`, then `reservation.fulfilled`) and for cancel (`reservation.cancelled`, then `reservation.ready`) | `book.retire` (`book.retired` first, then the events of the loans it closed) and `loan.return` |
| `test_return_without_a_queue_does_not_emit_ready`, `test_checkout_without_a_reservation_emits_one_event` | no event when nothing happened | every op |
| `test_a_held_copy_is_not_available`, `test_two_copies_two_ready`, `test_cancelling_the_last_ready_reservation_frees_the_copy` | `available` in the book view is what `loan.checkout` compares with; a held copy lowers it | `views.available` used by `loan.checkout`; prompt ("not available to anyone else") |
| `test_checkout_by_the_holder_fulfils`, `test_checkout_by_someone_else_changes_nothing` | the holder's own held copy counts for them; fulfilling bumps the reservation | prompt |
| `test_the_other_book_is_not_touched`, `test_a_cancelled_reservation_is_skipped_on_return` | queue is per book and only `waiting` reservations count | prompt |
| `test_retire_still_orders_its_events`, `test_late_fine_order_is_unchanged`, `test_return_value_is_unchanged`, `test_retrieve_emits_nothing` | regression; reads emit no events | `ops/books.py`, `loans.py`; `tests/test_lendr.py` |

Not tested on purpose, because the repo does not decide it: the order of `fine.charged` against
`reservation.ready` is only checked as a set; what `book.retire` does to reservations; `param` for the
"free copy" and "already has it" conflicts; `pickup_by` after a cancel.

What makes it hard: a hand-off has to happen on every path that frees a copy (`loan.return`,
`reservation.cancel`; `book.retire` goes through `loans.close` too), the view's `available` has to drop
for held copies and the holder has to get past that check, and the events have to follow the
own-event-first order that `book.retire` and `loan.return` show. The easy-looking version emits
`reservation.ready` before `loan.returned`, or hands over only in `loan.return`, or forgets that
checkout must fulfil.
