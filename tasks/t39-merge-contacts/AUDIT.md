# t39-merge-contacts: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for `contact.merge` on an address book and leaves four product
decisions open. They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool).
Everything else is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operation_is_registered` | registered by name; module imported in `ops/__init__.py` | prompt (name); `ops/__init__.py` comment; `ops/registry.py` |
| `test_returns_the_primary_view` | merge returns the primary's view | prompt ("It returns the primary contact") |
| `test_primary_is_bumped` | every change goes through `store.bump` (version + 1, `updated_at`) | `contact.update` in `ops/contacts.py` |
| `test_event` | one event `contact.merged`, data `{"contact": return value, "duplicate": view}` | event naming and `{"<noun>": view}` in `ops/`; prompt words `primary`/`duplicate` |
| `test_unknown_contacts`, `test_missing_arguments`, `test_arguments_are_stripped` | `store.get_contact` raises NotFound with param `contact`; ids read with `require_str` (InvalidRequest, param = argument name, stripped) | `store.get_contact`, `ops/contacts.py` |
| `test_failures_change_nothing`, `test_other_contacts_untouched` | check before changing; no event on failure | every op in `ops/` |
| `TestWinner` (7) | name and company: the more recently updated contact wins (by updated_at), tie to primary, blank never replaces | answers.json `winner` |
| `TestLists` (8) | union, primary first, then duplicate's new entries; emails case-insensitive, phones by digits, first-seen form kept; duplicate keeps its own lists; views return copies | answers.json `lists`; copies: `views.contact_view` uses `list(...)` |
| `TestDuplicateRecord` (11) | tombstone: `status` `merged`, `merged_into`, bumped, hidden from `contact.list`, retrievable; update, log and merge on it are a Conflict (param `contact`, `primary`, `duplicate`); self merge InvalidRequest on `duplicate`; failures change nothing | answers.json `duplicate_record`; `errors.Conflict` |
| `TestActivities` (7) | activities re-pointed to the primary with ids and times kept, time order then id, duplicate's list empty, merge logs nothing | answers.json `activities`; `store.activities_for` sorts by `(at, id)` |
| `TestRegression` | existing behaviour stays | `tests/test_contacts.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| winner | newer `updated_at` wins, tie primary, blank never wins | primary always wins; duplicate always wins; primary wins unless blank; longer value wins | 4 (`newer_duplicate_wins`, `decided_by_updated_at`, `blank_company_filled`, `blank_never_replaces`) | about 15% (primary-unless-blank is the usual guess and fails the two "newer" tests) |
| lists | union, case-insensitive emails, digits-only phones, first spelling kept | plain union with exact-string compare; lowercase emails when storing; sorted lists; duplicate's first | 6 | about 20% |
| duplicate_record | tombstone with `status`/`merged_into`, hidden from list, Conflict on reuse | hard delete (retrieve then fails NotFound); keep it listed; delete it and keep a redirect | 10 | hard delete about 50%, and even a tombstone guess needs the exact field names and error params: about 5% |
| activities | move to primary, duplicate empty | leave them where they are; copy them to both; delete them | 6 | move about 45% (the exact ordering rule is already in the repo) |

A guess passes only if every decision is right: about 0.1%.

What makes it hard: a merge looks like one small function, but every field has a collision rule and the
duplicate record itself has to go somewhere. The prompt says "somewhere sensible" for each, which is
true of several different designs, and only the owner's answers pick one.

## Keyword self-check

Matching returns every entry with at least one keyword hit, so each keyword must point at its own
decision. Generated with `ate.askuser.server._hits` over `answers.json`: for each phrasing, the ids
that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| If the two contacts have different names, which value wins? | winner | winner |
| Which company should be kept when they disagree? | winner | winner |
| Should the newer record override the older one? | winner | winner |
| How should emails be combined, and are they case sensitive? | lists | lists |
| Do I dedupe phone numbers, and how do I compare them? | lists | lists |
| Should the merged phones keep a particular list order? | lists | lists |
| Should the duplicate be deleted after the merge? | duplicate_record | duplicate_record |
| What happens to the duplicate record afterwards? | duplicate_record | duplicate_record |
| Can a merged contact be merged again? | duplicate_record | duplicate_record |
| Is it a soft delete or a hard delete? | duplicate_record | duplicate_record |
| What happens to the duplicate's logged calls and meetings? | activities | activities |
| Should the activity history move to the primary? | activities | activities |
| Where do the duplicate's activities go? | activities | activities |
| Should the event be named contact.merged? | (none: not a decision) | none |
| What should merge return? | (none: not a decision) | none |
| Which error should a bad id raise? | (none: not a decision) | none |
