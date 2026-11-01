from datetime import timedelta

from .errors import NotFound

PICKUP = timedelta(hours=72)


class Store:
    def __init__(self):
        self.members = {}
        self.books = {}
        self.loans = {}
        self.holds = {}

    def get_member(self, member_id, param="member"):
        member = self.members.get(member_id)
        if member is None:
            raise NotFound(f"no member {member_id!r}", param=param)
        return member

    def get_book(self, book_id, param="book"):
        book = self.books.get(book_id)
        if book is None:
            raise NotFound(f"no book {book_id!r}", param=param)
        return book

    def get_loan(self, loan_id):
        loan = self.loans.get(loan_id)
        if loan is None:
            raise NotFound(f"no loan {loan_id!r}", param="loan")
        return loan

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def open_loan_of(self, book_id):
        """The open loan on this book, or None when it is on the shelf."""
        for loan in self.loans.values():
            if loan.book == book_id and loan.status == "open":
                return loan
        return None

    def open_loans_of(self, member_id):
        return sorted((l for l in self.loans.values() if l.member == member_id and l.status == "open"),
                      key=lambda l: (l.created_at, l.id))

    def get_hold(self, hold_id):
        hold = self.holds.get(hold_id)
        if hold is None:
            raise NotFound(f"no hold {hold_id!r}", param="hold")
        return hold

    def active_holds_of(self, member_id):
        return [h for h in self.holds.values() if h.member == member_id and h.status in ("waiting", "ready")]

    def ready_hold_of(self, book_id):
        for hold in self.holds.values():
            if hold.book == book_id and hold.status == "ready":
                return hold
        return None

    def offer_next(self, book_id, at):
        """Offer the book to the first waiting hold in line, from the moment `at`."""
        line = sorted((h for h in self.holds.values() if h.book == book_id and h.status == "waiting"),
                      key=lambda h: (h.created_at, h.id))
        if line:
            line[0].status = "ready"
            line[0].expires_at = at + PICKUP
            self.bump(line[0], at)

    def expire_holds(self, now):
        """Lapse every ready hold whose time is up; the next in line is offered the book as it lapses."""
        changed = True
        while changed:
            changed = False
            for hold in sorted(self.holds.values(), key=lambda h: (h.expires_at or now, h.id)):
                if hold.status == "ready" and hold.expires_at <= now:
                    hold.status = "expired"
                    self.bump(hold, now)
                    self.offer_next(hold.book, hold.expires_at)
                    changed = True
                    break
