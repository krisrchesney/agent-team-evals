# t42-book-holds: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for holds (a waiting line) on a library and leaves five decisions
open. They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool). Everything
else is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | four operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_hold_view` | id `hold_0001`, `ids.new("hold")`; created_at = updated_at = now, version 1; `book`, `member`, `status` | prompt (fields, `waiting`); `ids.py`; `views.stamp`; `ops/members.py` |
| `test_place_event` | one event `hold.placed`, data `{"hold": view}` equal to the return value | `service.call` docstring (past tense of the operation, one event, last) |
| `test_unknown_book_and_member` | NotFound with param = argument name; ids read with `require_str` | `store.get_book` / `get_member`; `ops/loans.py` |
| `test_failures_change_nothing` | no event and no id taken on failure | `service.call` docstring |
| `test_retrieve` | read by `hold`, reads emit nothing, NotFound / InvalidRequest on `hold` | prompt; `loan.retrieve`; docstring |
| `TestQueue` return, line, ready | the first hold placed is offered the book on return (`ready`); order is placement order; others stay `waiting` | prompt (bullet 3) |
| `test_ready_book_cannot_be_borrowed_by_others` | borrow of a reserved book is a Conflict on `book` | prompt (nobody else can borrow it); `loan.borrow` already raises Conflict on `book` |
| `test_collect_borrows_the_book` | collected, a normal loan (`loan_0002`, due now + 14 days, open), hold version 3 (placed, readied, collected), one event `hold.collected` only | prompt ("a normal loan"); `LOAN_DAYS` in `ops/loans.py`; docstring (bump on every change; other records change silently) |
| `test_collect_only_when_ready` | collecting a waiting hold is a Conflict on `hold` | prompt ("collecting a ready hold"); `loan.return` raises Conflict on its id param when the state is wrong |
| `test_cancel_*`, `test_cancelling_*` | cancelled, version 2, event `hold.cancelled`; a cancelled ready hold passes the book to the next in line; the last one frees the book | prompt (bullet 3); docstring |
| `test_return_emits_only_the_loan_event` | return emits one event, `loan.returned`; the hold turning ready is silent | docstring ("other records the call changes along the way change silently") |
| `test_a_hold_that_is_done_...`, `test_unknown_hold`, `test_other_books_are_independent` | Conflict on `hold` for finished holds; NotFound / InvalidRequest | `loan.return`; `store.get_*`; prompt |
| `TestPickup` (9) | ready for 72 hours, `expires_at` in the view (null while waiting), expired from that moment inclusive, seen by every operation, cannot be collected or cancelled, next in line offered at the lapse moment (cascade), no event, done holds never expire | answers.json `pickup` (event rule: docstring) |
| `TestLimit` (5) | at most 3 active (waiting or ready) holds per member; Conflict on `member`; cancelled, collected and expired don't count | answers.json `limit` |
| `TestShelf` (3) | hold on a free book is a Conflict on `book`; a book reserved by a ready hold is not free; a lapsed one is free again | answers.json `shelf` |
| `TestSameMember` (4) | no hold on a book you have on loan or already hold actively (waiting or ready); fine again after cancelling | answers.json `same_member` |
| `TestOverdue` (4) | overdue loan blocks placing; overdue = strictly after due; returned loans don't count; existing holds and collecting unaffected | answers.json `overdue`; `due` in `loan_view` |
| `TestRegression` | existing behaviour stays | `tests/test_lending.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| pickup | 72 h from ready, `expires_at`, cascade at the lapse moment | no expiry; 24, 48 h, 7 days; next in line offered when noticed | 8 | about 3% (exact length plus cascade timing and the view field) |
| limit | 3 active holds per member | no limit; 5; counting only waiting | 3 | no limit 45%; exactly 3 with ready counted about 8% |
| shelf | refuse a hold on a free book | allow it (ready at once, or waiting) | 3 | about 35% for refusing; param `book` likely, but the reserved-book nuance 70% of those |
| same_member | refuse own-loan and duplicate holds | allow either; refuse one of the two | 4 | about 25% for refusing both |
| overdue | overdue blocks placing; strict | no check; also block collecting; non-strict | 3 | no check 55%; the strict check about 15% |

A guess passes only if every decision is right: well under 1%.

What makes it hard: holds look like a simple queue. The decisions are the lifecycle rules around it (how
long a book is kept, who may join, when), and the lapse rule has a cascade (the next in line is offered
the book at the moment the earlier hold lapsed) that only the answer sheet states.

## Keyword self-check

The server answers with every entry that has at least one keyword hit, so each keyword must point at its
own decision. Generated with `ate.askuser.server.match_answer` over `answers.json`: for each phrasing, the
ids that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| How long is a ready hold kept for the member to pick it up? | pickup | pickup |
| What happens if the member never comes to collect the book? | pickup | pickup |
| Should holds expire? | pickup | pickup |
| Is there a time window to collect after it becomes ready? | pickup | pickup |
| Is there a limit on how many holds one member can have? | limit | limit |
| What is the maximum number of holds per person? | limit | limit |
| Can a member hold too many books at once? | limit | limit |
| Can someone place a hold on a book that is on the shelf? | shelf | shelf |
| What if the book is available right now? | shelf | shelf |
| Should I refuse holds when the book is not out? | shelf | shelf |
| Can a member hold a book they already have borrowed? | same_member | same_member |
| Can the same member place two holds on the same book? | same_member | same_member |
| What if a member already holds this title? | same_member | same_member |
| Can a member with overdue loans place a hold? | overdue | overdue |
| Should members who owe late books be blocked? | overdue | overdue |
| Are members in good standing the only ones who can hold? | overdue | overdue |
| What should the hold id look like? | (none: not a decision) | none |
| Which event is emitted when a hold is collected? | (none: not a decision) | none |
| Should the next member be offered the book when it is returned? | (none: not a decision) | none |
| Does collecting create a loan? | (none: not a decision) | none |
