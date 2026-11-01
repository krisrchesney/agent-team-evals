Members keep missing the books they want because every copy is out. Add reservations to `lendr`:

- `reservation.create` puts a member in line for a book. It takes `book` and `member`.
- `reservation.cancel` and `reservation.retrieve` take the reservation's id as `reservation`.
- Each of them returns the reservation. A reservation is `waiting`, `ready`, `fulfilled` or
  `cancelled`. Only a book with no copy available can be reserved, and members are served in the
  order they reserved.
- When a copy comes back and someone is waiting, the first in line gets it: their reservation turns
  `ready` and the copy is held for them until `pickup_by`, 3 days later. A held copy is not available
  to anyone else. The reservation is `fulfilled` when that member checks the book out. If a ready
  reservation is cancelled, the copy goes to the next in line.

Build it the way the rest of `lendr` is built, so it fits with everything else in the service.
Existing behaviour must keep working. Use only the Python standard library. Existing tests are in
`tests/`.
