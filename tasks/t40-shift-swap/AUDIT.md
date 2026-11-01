# t40-shift-swap: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for shift swaps on a rota and leaves four decisions open. They
are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool). Everything else is
shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | five operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_swap_view` | id `swap_0001` from `svc.ids.new("swap")`; created_at = updated_at = now, version 1; fields named in the prompt (`shift`, `to_staff`, `status`) plus `from_staff` | `ids.py`, `views.stamp`, `ops/shifts.py`; `from_staff` is the holder at request time (the only other person in the prompt's story) |
| `test_request_event`, resolve events | one event per mutation, `<noun>.<past tense>`, data `{"<noun>": view}` equal to the return value; accept also carries the changed shift | `shift.created`, `staff.created` in `ops/` |
| `test_unknown_shift_and_staff`, `test_missing_arguments` | `get_shift` / `get_staff` NotFound with param = argument name (`to_staff` for the recipient), ids read with `require_str` | `store.get_staff(..., param=)`, `ops/shifts.py` |
| `test_not_to_the_current_holder` | InvalidRequest on `to_staff` | prompt |
| `test_failures_change_nothing`, `test_conflict_changes_nothing` | check before changing; ids taken after validation; no event on failure | every op in `ops/` |
| `TestResolve` | accept moves the shift (`store.bump` on shift and swap), decline and cancel leave it, a swap that is not pending is a Conflict on `swap` | prompt; `store.bump`; `errors.Conflict` |
| `test_retrieve` | read by `swap`, reads emit nothing | `shift.retrieve` |
| `TestNotice` (5) | at least 24 hours before the shift start, inclusive, Conflict on `shift`, checked at request time only | answers.json `notice` |
| `TestLapse` (7) | lapses at the earlier of request + 48 h and the shift start, expired from that moment, seen by every operation, no event, `expires_at` in the view | answers.json `lapse` |
| `TestRest` (11) | 10 hours between the taker's other shifts and this one (end to start, either side, inclusive), overlap and back-to-back refused, only on accept, swap stays pending, the swapped shift itself ignored | answers.json `rest`; `store.clashes` and its overlap rule in `ops/shifts.py` |
| `TestOnePending` (5) | one pending swap per shift, Conflict on `shift`, nothing replaced, other shifts independent, free again after any way out | answers.json `one_pending` |
| `TestRegression` | existing behaviour stays | `tests/test_rota.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| notice | 24 h before start, inclusive | no minimum; 12, 24 or 48 h; exclusive bound | 4 | no minimum 40%; 24 h inclusive about 15% |
| lapse | earlier of 48 h and shift start, `expires_at` | no expiry; 24 h; 48 h only; 7 days; expire when the shift starts | 7 | about 8% (exact value and the "shift start" cap together) |
| rest | 10 h between shifts, on accept, Conflict on `to_staff` | only the overlap check the repo already has; 8, 11 or 12 h; check on request as well | 8 | about 25% for overlap-only (fails the 10 h tests), 10 h exact about 5% |
| one_pending | one per shift, refuse the second | allow several; the new one replaces the old; the new one cancels the old | 3 | refuse about 40% (param `shift` likely) |

A guess passes only if every decision is right: well under 1%.

What makes it hard: the request reads like plain state-machine work (request, accept, decline, cancel).
The decisions are the timing and eligibility rules around it, and each has a boundary (inclusive or not)
that the tests pin down.
