def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def member_view(member):
    return {"id": member.id, "name": member.name, "created_at": stamp(member.created_at),
            "updated_at": stamp(member.updated_at), "version": member.version}


def book_view(book):
    return {"id": book.id, "title": book.title, "created_at": stamp(book.created_at),
            "updated_at": stamp(book.updated_at), "version": book.version}


def loan_view(loan):
    return {"id": loan.id, "book": loan.book, "member": loan.member, "status": loan.status,
            "due": stamp(loan.due), "created_at": stamp(loan.created_at),
            "updated_at": stamp(loan.updated_at), "version": loan.version}
