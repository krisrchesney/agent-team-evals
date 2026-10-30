# Monthly statements

A statement is what the customer reads, so it follows the customer's calendar, not the server's.

1. **Period.** A statement covers one calendar month in the account's local time
   (`Account.utc_offset_minutes`): from 00:00 local time on the 1st, up to but not including 00:00
   local time on the 1st of the next month.
2. **Which transactions count.** Only `posted` transactions; `pending` ones never appear and never
   affect a balance. A transaction that was amended counts once, as its latest version (see
   `docs/FEED.md`). These rules apply everywhere: to the lines and to both balances.
3. **Balances.** The opening balance is the sum of all counted transactions posted before the
   period starts. The closing balance is the opening balance plus the lines. So each month's closing
   balance equals the next month's opening balance.
4. **Lines.** One line per counted transaction posted within the period, ordered by posting time,
   then by `external_id`.
5. **Dates on the statement** are local dates in the account's time zone (`YYYY-MM-DD`), like the
   period itself.
6. **Amounts** are integer cents; money in is positive, money out is negative.
