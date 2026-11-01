def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def available(svc, book):
    """Copies that can be checked out right now."""
    return book.copies - len(svc.store.open_loans(book_id=book.id))


def book_view(svc, book):
    return {
        "id": book.id,
        "title": book.title,
        "copies": book.copies,
        "available": available(svc, book),
        "status": book.status,
        "created_at": stamp(book.created_at),
        "updated_at": stamp(book.updated_at),
        "version": book.version,
    }


def member_view(member):
    return {
        "id": member.id,
        "name": member.name,
        "status": member.status,
        "created_at": stamp(member.created_at),
        "updated_at": stamp(member.updated_at),
        "version": member.version,
    }


def loan_view(loan):
    return {
        "id": loan.id,
        "book": loan.book,
        "member": loan.member,
        "status": loan.status,
        "due": stamp(loan.due),
        "returned_at": stamp(loan.returned_at) if loan.returned_at else None,
        "created_at": stamp(loan.created_at),
        "updated_at": stamp(loan.updated_at),
        "version": loan.version,
    }


def fine_view(fine):
    return {"id": fine.id, "loan": fine.loan, "member": fine.member, "amount": fine.amount,
            "created_at": stamp(fine.created_at)}
