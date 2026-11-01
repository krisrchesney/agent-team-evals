from .errors import NotFound


class Store:
    def __init__(self):
        self.members = {}
        self.books = {}
        self.loans = {}

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
