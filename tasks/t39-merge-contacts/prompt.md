Our address book fills up with duplicates: the same person gets added twice. Add `contact.merge` to
`addrbook`:

- It takes `primary` and `duplicate`, both contact ids, and folds the duplicate into the primary.
- It returns the primary contact.
- Emails, phones, company, name and the logged activities all have to end up somewhere sensible.

Build it the way the rest of `addrbook` is built. Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.

The product owner who wrote this request can be asked questions through the `ask_user` tool. Several
product decisions here are open on purpose: ask about them instead of guessing.
