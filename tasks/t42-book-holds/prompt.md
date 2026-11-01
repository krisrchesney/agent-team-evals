Members keep asking the desk for books that are out. Add holds to `lending`:

- `hold.place` takes `book` and `member`: the member joins the line for a book that is out.
- `hold.cancel`, `hold.collect` and `hold.retrieve` take the hold's id as `hold`.
- Holds are served in the order they were placed. When a book comes back, the first member in line is
  offered it: their hold becomes `ready`, and nobody else can borrow that book until the hold is collected
  or goes away. Collecting a ready hold borrows the book to that member (a normal loan). If the member who
  was offered the book cancels, the next in line is offered it.
- Each of them returns the hold, which shows its `book`, `member` and `status`. A hold is
  `waiting`, `ready`, `collected` or `cancelled`.

Build it the way the rest of `lending` is built. Existing behaviour must keep working. Use only the Python
standard library. Existing tests are in `tests/`.

The desk manager who wrote this request can be asked questions through the `ask_user` tool. Several
decisions here are open on purpose: ask about them instead of guessing.
