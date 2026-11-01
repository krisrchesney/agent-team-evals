from .errors import NotFound


class Store:
    def __init__(self):
        self.books = {}
        self.members = {}
        self.loans = {}
        self.fines = {}
        self.reservations = {}

    def get_book(self, book_id):
        book = self.books.get(book_id)
        if book is None:
            raise NotFound(f"no book {book_id!r}", param="book")
        return book

    def get_member(self, member_id):
        member = self.members.get(member_id)
        if member is None:
            raise NotFound(f"no member {member_id!r}", param="member")
        return member

    def get_loan(self, loan_id):
        loan = self.loans.get(loan_id)
        if loan is None:
            raise NotFound(f"no loan {loan_id!r}", param="loan")
        return loan

    def get_reservation(self, reservation_id):
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise NotFound(f"no reservation {reservation_id!r}", param="reservation")
        return reservation

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def open_loans(self, book_id=None, member_id=None):
        """Open loans, oldest id first."""
        return [loan for _, loan in sorted(self.loans.items())
                if loan.status == "open"
                and (book_id is None or loan.book == book_id)
                and (member_id is None or loan.member == member_id)]

    def reservations_for(self, book_id, *statuses):
        """Reservations of a book in these states, in the order they were placed."""
        return [r for _, r in sorted(self.reservations.items())
                if r.book == book_id and r.status in statuses]
