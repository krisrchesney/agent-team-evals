# t44-expense-approvals: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for approvals on expense claims and leaves five decisions open.
They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool). Everything else
is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | three operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_submit` | `submitted`, version 2, updated_at = now; one event `expense.submitted`, data `{"expense": view}` equal to the return value | prompt (statuses); `service.call` docstring (bump, past tense, one event) |
| `test_unknown_and_missing_expense` | NotFound / InvalidRequest on `expense`; ids read with `require_str` | `store.get_expense`; `ops/expenses.py` |
| `test_approve_and_reject_need_a_known_by` | NotFound on `by` for an unknown employee, InvalidRequest when missing | prompt (`by` names an employee); `store.get_employee(..., param=)` as used for `manager` in `ops/employees.py` |
| `test_failures_change_nothing` and the "refusal changes nothing" asserts | no event, no version change when a call raises | `service.call` docstring |
| `TestWho` (6) | the direct manager approves or rejects (approved = submitted + 1 bump, version 3, events `expense.approved` / `expense.rejected`); anybody else is a Conflict on `by`; no manager means no submitting (Conflict on `expense`); only a submitted expense can be decided (Conflict on `expense`) | answers.json `who`; events and version: docstring |
| `TestSecond` (9) | 50000 cents or more needs the manager then the manager's manager; `approvals` list; stays `submitted` after the first; just under needs one; order enforced for approving and rejecting; a manager at the top is enough | answers.json `second` |
| `TestWindow` (5) | submit up to 30 calendar days (UTC) after `date`, day 31 refused (Conflict on `expense`); future dates fine; only checked at submit | answers.json `window` |
| `TestDuplicate` (6) | same employee, amount and date as a `submitted` or `approved` expense is refused; drafts and rejected don't count; only drafts can be submitted | answers.json `duplicate` |
| `TestReason` (3) | reject needs a non-empty string `reason` (InvalidRequest on `reason`), shown as `reason`, null otherwise | answers.json `reason` |
| `TestRegression` | existing behaviour stays | `tests/test_expenses.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| who | direct manager only; anyone else Conflict on `by`; no manager, no submitting | any employee but the submitter; any manager; no check; param other than `by` | 6 | about 15% (direct manager and the exact conflict shapes) |
| second | 50000 or more: manager then manager's manager, in order, `approvals` in the view | single approval; other thresholds (100, 1000); either order | 9 | no second step 45%; the exact 50000 inclusive and order about 5% |
| window | 30 calendar days, day 31 refused | no window; 14, 60, 90 days; counting from creation | 5 | no window 50%; exactly 30 about 8% |
| duplicate | submitted or approved with the same amount and date refuses; drafts and rejected do not | no duplicate check; also match description; count rejected | 4 | no check 55%; exact definition about 10% |
| reason | required non-empty `reason`, shown in the view | no reason; optional reason | 3 | no reason 50%; required about 15% |

A guess passes only if every decision is right: well under 1%.

What makes it hard: submit, approve and reject look like a three-state machine. The decisions are the
control rules around it (who may decide, when a second signature is needed, how old a claim may be, what
counts as a duplicate), and each has an exact boundary or shape that the tests pin down.

## Keyword self-check

The server answers with every entry that has at least one keyword hit, so each keyword must point at its
own decision. Generated with `ate.askuser.server.match_answer` over `answers.json`: for each phrasing, the
ids that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| Who is allowed to approve an expense? | who | who |
| Can employees approve their own expenses? | who | who |
| What if an employee has no manager? | who | who |
| Do large expenses need a second approval? | second | second |
| Is there an amount threshold that needs escalation to a director? | second | second |
| Do big expenses need two approvers? | second | second |
| How old can an expense be when it is submitted? | window | window |
| Is there a deadline after the expense date for submitting? | window | window |
| Should I refuse expenses that are too old? | window | window |
| Should duplicate expenses be refused? | duplicate | duplicate |
| Can a rejected expense be resubmitted? | duplicate | duplicate |
| What if the same amount on the same date is submitted twice? | duplicate | duplicate |
| Does a rejection need a reason? | reason | reason |
| Should the rejection carry a comment? | reason | reason |
| Why was it rejected, should we store an explanation? | reason | reason |
| What should the expense id look like? | (none: not a decision) | none |
| Which event is emitted when an expense is submitted? | (none: not a decision) | none |
| What status does a submitted expense have? | (none: not a decision) | none |
| What is the status after approving? | (none: not a decision) | none |
