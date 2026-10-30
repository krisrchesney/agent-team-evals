`bookings` is a small meeting-room booking system. `BookingService` (in `service.py`) is the only
place that changes state: it uses a `Store` (rooms, users, teams, bookings), a `Clock` that tells it
what time it is, and an `Outbox` that collects messages for users. `rules.py`, `permissions.py`,
`billing.py`, `fmt.py` and `report.py` hold the rules, who-may-do-what, prices and fees, text
formats and reports. Money is integer cents, times are naive `datetime`s, and a team's budget is
what it has left to spend. This task adds recurring bookings, cancellation fees and a waitlist.
Every rule is numbered (R1, R2, ...) and every number in it matters; the existing messages and
formats must stay exactly as they are unless a rule says otherwise.

**Behaviour that exists today and must not change (R1).** `book(user_id, room_id, start, end,
attendees)` checks, in this order: unknown user, unknown room, permissions (guests may not book; staff
may not book premium rooms), the time slot (end after start; both on 15-minute marks; 30 to 240 minutes;
one weekday between 08:00 and 18:00), attendees (1 up to the room's capacity), lead time (at least 15
minutes from now), that the room is free (bookings that merely touch end to start do not conflict),
and the team budget; the error messages are the ones in the code. A booking costs the room's hourly
rate for its minutes, rounded half up to a cent. Booking sends the user `Booked: <room>` with the body
`<slot> for <n> attendees, <money>`, and it says `attendees` even when n is 1. Cancelling by someone who
may do so (admins any booking, managers their team's, others their own) marks the booking cancelled,
gives money back to the team and sends the owner `Cancelled: <room>`.
The utilization and agenda reports and the free-slot finder keep working as they do.

**Recurring bookings.** A new `BookingService.book_series(user_id, room_id, start, end, attendees,
repeat, count)` books the same slot `count` times and returns the list of new bookings in time order.
`repeat` is `weekly` (occurrences 7 days apart) or `biweekly` (14 days apart) (R2). Anything else
for `repeat` raises `InvalidRequest("repeat must be 'weekly' or 'biweekly'")`, and a `count` that is not
an integer from 2 to 12 raises `InvalidRequest("count must be between 2 and 12")`; `repeat` is
checked first, and both come after the unknown-user and unknown-room errors and before everything
else (R3). The permission rules apply in this order: guests (`guests cannot book rooms`), then staff
(`NotAllowed("only managers can book series")`), then staff and premium rooms (R4). Each occurrence is checked
with the slot, attendees, lead time and room-free rules of a single booking, in that order, occurrence 1 first;
the first problem found is raised as the same kind of error with `occurrence N: ` (N counts from 1) put in
front of its message, for example `occurrence 3: room is already booked from 09:00 to 10:00` (R5). A series
is all or nothing: if anything fails, nothing is booked, charged or sent (R6). Bookings of a series carry a
`series_id`, a new field on `Booking` that is `None` for every other booking; the first series ever booked
gets 1, the next 2, and so on, counted separately from booking ids (R7).
A series of 4 or more occurrences gets 10% off: each occurrence's price is its normal price times 0.9
rounded half up to a cent, and that discounted price is what the booking's `cost_cents` holds; shorter series
pay the normal price (R8). The team budget is checked once against the total of the discounted prices; a short
budget raises the usual `team budget too low: need <total>, have <budget>` message with that total, and a
sufficient one is charged that total once (R9). One message goes to the user, not one per occurrence: subject
`Series booked: <room>`, body `<count> bookings of <room>, first <slot of the first occurrence>, total <money>` (R10).

**Cancellation fees.** Cancelling now costs money when it is late. Measured from the clock's now to the
booking's start: at least 24 hours (exactly 24 hours included) means no fee; at least 2 hours but less than
24 means the team keeps half of the cost, rounded half up to a cent; less than 2 hours means it keeps all of it
(R11). The team gets back the cost minus the fee, so `budget_cents` rises by that and `spent_cents` falls by
that; `Team` gets a new field `fees_cents` that grows by every fee kept (the fee stays inside `spent_cents`) (R12).
Cancelling a booking whose start is now or already past raises `InvalidRequest("booking has already started")`;
the checks run in the order permission, already cancelled, already started (R13). The single-booking message body
is `<slot>, refund <money>`, followed by `, fee <money>` only when the fee is above zero (R14).

**Cancelling a series.** `cancel(user_id, booking_id, series=False)` gets a `series` flag. With
`series=True` on a booking that belongs to a series, that booking and every later active occurrence of the same
series (starting at or after it) are cancelled; earlier occurrences and occurrences already cancelled are left
alone, and each cancelled occurrence has its own fee worked out from its own start (R15). The permission,
cancelled and started checks apply to the booking that was named, and then one message goes to its owner:
subject `Series cancelled: <room>`, body `<n> bookings cancelled, refund <money>, fee <money>` with the totals,
the fee shown even when it is $0.00 (R16). `cancel` returns the cancelled `Booking`; with `series=True` it returns
a list of cancelled bookings, and for a booking that is not in a series that list has the one booking and the
normal single-booking message is sent (R17).

**Waitlist.** `book` takes a new keyword `waitlist=False`. If it is true and the *only* thing wrong is that the room
is taken (every earlier check passed), the request is put on the waitlist instead of raising: a
`WaitlistEntry` (in `bookings.models`, a frozen dataclass with `id`, `user_id`, `room_id`, `start`, `end`,
`attendees`, `created`, where `created` is the clock's now) is stored in `store.waitlist` (a dict from entry id to entry), entry ids count from 1
independently of the other ids, nothing is charged and the budget is not checked, the user gets `Waitlisted: <room>`
with the body `<slot> for <n> attendees`, and the entry is returned. Any other problem raises as before, and when
the room is free `book` books as usual and returns the `Booking` (R18). After a cancellation is completely done
(refunds made, messages sent, for a whole series after all its occurrences), the service goes through the waitlist
entries of that room in the order they were created (ties by id), and for each one: if it now starts less than 15
minutes from the clock's now, it is dropped; otherwise if it still collides with an active booking it stays; otherwise
if its user's team cannot afford it at the normal price it stays; otherwise it is booked at the normal price and
charged, removed from the waitlist, and its user is sent `Booked from waitlist: <room>` with the same body a normal
booking message has. Each entry sees the bookings made for the entries before it, and money refunded by the
cancellation is available to the teams (R19). A booking made from the waitlist is an ordinary one, with no
`series_id` and `created` set to the clock's now (R20). `leave_waitlist(user_id, entry_id)` removes an entry; an unknown entry raises
`NotFound("unknown waitlist entry <id>")`, and anyone but the entry's user gets
`NotAllowed("you cannot leave this waitlist entry")` (R21).

**Text formats and reports.** Money in messages, errors and reports is written with thousands
separators: `$1,234.56` (R22). `report.spend_report` lines get `, <money> in fees` appended when the team's `fees_cents`
is above zero (R23). A new `report.waitlist_report(store)` returns one line `<room name>: <n> waiting` for each room that has
waiting entries, sorted by room name case-insensitively, or `Waitlist is empty` when there are none (R24).
Several of these rules meet: the cancellation fee of a series occurrence is worked out from its discounted
cost; a refund from a cancellation can pay for a waitlisted booking of the same team; and the series
all-or-nothing rule (R6) means a failed series leaves the series counter and the booking ids untouched (R25).

Standard library only. Existing tests are in `tests/`.
