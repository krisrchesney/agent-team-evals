"""In-memory tables and the indexes that go with them.

A deleted row stays in its table. Every read here skips deleted rows unless told otherwise, and the
email index only holds live customers.
"""
from .errors import NotFound


def _visible(rows, include_deleted):
    return [r for r in rows if include_deleted or r.deleted_at is None]


class Store:
    def __init__(self):
        self.customers = {}
        self.tickets = {}
        self.comments = {}
        self._email = {}           # email -> id of the live customer using it
        self._by_customer = {}     # customer id -> {ticket id: None}, oldest first
        self._by_ticket = {}       # ticket id -> {comment id: None}, oldest first
        self._tagged = {}          # tag -> {ticket id: None}

    # lookups

    def customer(self, customer_id, include_deleted=False):
        found = self.customers.get(customer_id)
        if found is None or (found.deleted_at is not None and not include_deleted):
            raise NotFound(f"no customer {customer_id!r}", param="customer")
        return found

    def ticket(self, ticket_id, include_deleted=False):
        found = self.tickets.get(ticket_id)
        if found is None or (found.deleted_at is not None and not include_deleted):
            raise NotFound(f"no ticket {ticket_id!r}", param="ticket")
        return found

    def comment(self, comment_id, include_deleted=False):
        found = self.comments.get(comment_id)
        if found is None or (found.deleted_at is not None and not include_deleted):
            raise NotFound(f"no comment {comment_id!r}", param="comment")
        return found

    def customer_id_for_email(self, email):
        return self._email.get(email)

    def all_customers(self, include_deleted=False):
        return _visible(self.customers.values(), include_deleted)

    def all_tickets(self, include_deleted=False):
        return _visible(self.tickets.values(), include_deleted)

    def all_comments(self, include_deleted=False):
        return _visible(self.comments.values(), include_deleted)

    def tickets_of(self, customer_id, include_deleted=False):
        return _visible([self.tickets[i] for i in self._by_customer.get(customer_id, ())], include_deleted)

    def comments_of(self, ticket_id, include_deleted=False):
        return _visible([self.comments[i] for i in self._by_ticket.get(ticket_id, ())], include_deleted)

    def tickets_tagged(self, tag, include_deleted=False):
        return _visible([self.tickets[i] for i in self._tagged.get(tag, ())], include_deleted)

    # writes

    def add_customer(self, customer):
        self.customers[customer.id] = customer
        if customer.deleted_at is None:
            self._email[customer.email] = customer.id

    def set_email(self, customer, email):
        del self._email[customer.email]
        customer.email = email
        self._email[email] = customer.id

    def unindex_email(self, customer):
        if self._email.get(customer.email) == customer.id:
            del self._email[customer.email]

    def index_email(self, customer):
        self._email[customer.email] = customer.id

    def add_ticket(self, ticket):
        self.tickets[ticket.id] = ticket
        self._by_customer.setdefault(ticket.customer, {})[ticket.id] = None
        for tag in ticket.tags:
            self._tagged.setdefault(tag, {})[ticket.id] = None

    def retag(self, ticket, tags):
        for tag in ticket.tags:
            self._tagged[tag].pop(ticket.id, None)
        ticket.tags = tuple(tags)
        for tag in ticket.tags:
            self._tagged.setdefault(tag, {})[ticket.id] = None

    def move_ticket(self, ticket, customer_id):
        self._by_customer[ticket.customer].pop(ticket.id, None)
        ticket.customer = customer_id
        self._by_customer.setdefault(customer_id, {})[ticket.id] = None

    def add_comment(self, comment):
        self.comments[comment.id] = comment
        self._by_ticket.setdefault(comment.ticket, {})[comment.id] = None

    # permanent removal

    def drop_comment(self, comment_id):
        comment = self.comments.pop(comment_id)
        self._by_ticket[comment.ticket].pop(comment_id, None)

    def _drop_ticket_rows(self, ticket_id):
        ticket = self.tickets.pop(ticket_id)
        for tag in ticket.tags:
            self._tagged[tag].pop(ticket_id, None)
        for comment_id in list(self._by_ticket.pop(ticket_id, ())):
            del self.comments[comment_id]
        return ticket

    def drop_ticket(self, ticket_id):
        ticket = self._drop_ticket_rows(ticket_id)
        self._by_customer[ticket.customer].pop(ticket_id, None)

    def drop_customer(self, customer_id):
        """Remove the customer and everything that belongs to them."""
        customer = self.customers.pop(customer_id)
        self.unindex_email(customer)
        for ticket_id in list(self._by_customer.pop(customer_id, ())):
            self._drop_ticket_rows(ticket_id)
