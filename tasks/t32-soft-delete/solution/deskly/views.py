def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _deleted(row):
    return stamp(row.deleted_at) if row.deleted_at is not None else None


def customer_view(store, customer):
    return {"id": customer.id, "name": customer.name, "email": customer.email,
            "created_at": stamp(customer.created_at), "deleted_at": _deleted(customer),
            "ticket_count": len(store.tickets_of(customer.id))}


def ticket_view(store, ticket):
    return {"id": ticket.id, "customer": ticket.customer, "subject": ticket.subject, "body": ticket.body,
            "status": ticket.status, "priority": ticket.priority, "tags": list(ticket.tags),
            "created_at": stamp(ticket.created_at), "updated_at": stamp(ticket.updated_at),
            "deleted_at": _deleted(ticket), "comment_count": len(store.comments_of(ticket.id))}


def comment_view(comment):
    return {"id": comment.id, "ticket": comment.ticket, "author": comment.author, "text": comment.text,
            "created_at": stamp(comment.created_at), "deleted_at": _deleted(comment)}
