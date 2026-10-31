Support wants deleted customers, tickets and comments to be recoverable. Change `deskly` so that
deleting is soft, with a trash you can restore from and empty. Use only the Python standard library.
Everything else keeps working as it does today (tests are in `tests/`).

1. **Soft delete.** `delete_customer`, `delete_ticket` and `delete_comment` no longer remove the row.
   They mark it deleted with the clock's time and return the row's view. Every customer, ticket and
   comment view gets a `deleted_at` (`2026-03-01T09:00:00Z`, or `None` while the row is live). A
   deleted row is gone for all normal use: wherever the library takes an id of a deleted row it
   raises `NotFound` with the same `param` as for an unknown id. That includes `get_*`,
   `update_customer`, `find_customer`, status and tag changes, `add_comment`, `list_comments`,
   `open_ticket` for a deleted customer, `customer_summary`, `merge_customers`, and deleting it
   again. The events are unchanged: one `customer.deleted`, `ticket.deleted` or `comment.deleted`
   per call, with the same data (the counts are of the live rows that went with it).
2. **Cascade.** Deleting a customer deletes their live tickets and those tickets' live comments;
   deleting a ticket deletes its live comments. Rows deleted earlier keep their own `deleted_at`;
   rows that go with a parent get the parent's.
3. **Restore.** `restore_customer`, `restore_ticket` and `restore_comment` take the id, return the
   view and record `customer.restored` (data `id`, `tickets`: how many tickets came back),
   `ticket.restored` (`id`, `comments`) or `comment.restored` (`id`). A restore also brings back
   the rows that were deleted together with it, and only those: not a comment or ticket that was
   deleted earlier on its own. Restoring a row that is not deleted raises `Conflict` (`param` is
   `customer`, `ticket` or `comment`). Restoring a ticket whose customer is deleted is a `Conflict`
   (`param="customer"`), a comment whose ticket is deleted is a `Conflict` (`param="ticket"`), and a
   customer whose email a live customer now uses is a `Conflict` (`param="email"`); a failed restore
   changes nothing. An unknown id is `NotFound`.
4. **Email.** An email must be unique only among live customers: a deleted customer's email can be
   used again (`create_customer`, `update_customer`), and `find_customer` finds live customers only.
5. **Reads.** Deleted rows never show up in: `list_customers`, `list_tickets` (with or without the
   customer, tag or status filter), `list_comments`; the `ticket_count` and `comment_count` in views;
   `search_tickets` (a ticket matches and scores only on live text, so a deleted comment's words no
   longer count; deleted tickets never appear; restoring brings the old score back);
   `status_counts`, `tag_counts`, `customer_summary`, `aging`, `busiest_customers`; `tickets_csv` and
   `customers_csv` (including the `tickets` column). `stats` counts live rows only and gains
   `deleted`: `{"customers", "tickets", "comments"}` with the number of deleted rows of each kind.
   The activity feed is a history and is never filtered.
6. **Seeing deleted rows.** `get_customer`, `list_customers`, `get_ticket`, `list_tickets`,
   `list_comments`, `tickets_csv` and `customers_csv` take `include_deleted=False`; with `True` they
   include deleted rows, which carry their `deleted_at` (the two CSV exports then end with a
   `deleted_at` column, empty for live rows). `list_tickets(customer=<deleted id>,
   include_deleted=True)` works. Counts inside views stay counts of live rows.
7. **Merge.** `merge_customers(keep, drop)` moves every ticket of `drop` to `keep`, deleted ones too
   (so restoring such a ticket later works), and then deletes `drop`. Only `customer.merged` is
   recorded for it, as today. Both customers must be live.
8. **Tags.** `rename_tag` changes the tag on deleted tickets as well (they come back with the new
   tag) but returns, and records, only the number of live tickets it changed.
9. **Trash.** `trash(kind=None, limit=None)` returns `{"data": [...], "has_more": bool}` listing
   every deleted row, including rows that were deleted with a parent, most recently deleted first
   (ties: customers, then tickets, then comments, then the older id first; default limit 20). An item
   is `{"kind", "id", "label", "deleted_at"}`; the label is the customer's name, the ticket's subject
   or the comment's text cut to its first 40 characters. `kind` (`customer`, `ticket` or `comment`)
   filters; anything else is `InvalidInput` (`param="kind"`).
10. **Purge.** `purge(kind, id)` permanently removes a deleted row and returns
    `{"id": id, "purged": True}` after recording `<kind>.purged` (data `id`). Purging a customer also
    removes all of its tickets and their comments, deleted or not; purging a ticket removes its
    comments. A live row is a `Conflict` (`param` is the kind), an unknown id is `NotFound`, a bad kind
    is `InvalidInput`. Ids are never reused, purged or not.
11. **Retention.** `purge_expired()` purges every row deleted more than 30 days before now (exactly 30
    days ago stays), by the rules of `purge`. It returns `{"purged": {"customers": n, "tickets": n,
    "comments": n}}` counting every row that was removed, and records one `trash.purged` event with
    those counts if anything was removed.
12. **Save and load.** `dump()` keeps deleted rows and whatever `restore` needs, so after `load()`
    everything above still works. Older dumps with no deleted rows load as all live.
