"""In-memory tables and the indexes that go with them."""
from .errors import NotFound


class Store:
    def __init__(self):
        self.customers = {}
        self.tickets = {}
        self.comments = {}
        self._email = {}           # email -> customer id
        self._by_customer = {}     # customer id -> {ticket id: None}, oldest first
        self._by_ticket = {}       # ticket id -> {comment id: None}, oldest first
        self._tagged = {}          # tag -> {ticket id: None}

    # lookups

    def customer(self, customer_id):
        found = self.customers.get(customer_id)
        if found is None:
            raise NotFound(f"no customer {customer_id!r}", param="customer")
        return found

    def ticket(self, ticket_id):
        found = self.tickets.get(ticket_id)
        if found is None:
            raise NotFound(f"no ticket {ticket_id!r}", param="ticket")
        return found

    def comment(self, comment_id):
        found = self.comments.get(comment_id)
        if found is None:
            raise NotFound(f"no comment {comment_id!r}", param="comment")
        return found

    def customer_id_for_email(self, email):
        return self._email.get(email)

    def tickets_of(self, customer_id):
        return [self.tickets[i] for i in self._by_customer.get(customer_id, ())]

    def comments_of(self, ticket_id):
        return [self.comments[i] for i in self._by_ticket.get(ticket_id, ())]

    def tickets_tagged(self, tag):
        return [self.tickets[i] for i in self._tagged.get(tag, ())]

    # writes

    def add_customer(self, customer):
        self.customers[customer.id] = customer
        self._email[customer.email] = customer.id

    def set_email(self, customer, email):
        del self._email[customer.email]
        customer.email = email
        self._email[email] = customer.id

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

    def drop_comment(self, comment_id):
        comment = self.comments.pop(comment_id)
        self._by_ticket[comment.ticket].pop(comment_id, None)

    def drop_ticket(self, ticket_id):
        ticket = self.tickets.pop(ticket_id)
        self._by_customer[ticket.customer].pop(ticket_id, None)
        for tag in ticket.tags:
            self._tagged[tag].pop(ticket_id, None)
        for comment_id in list(self._by_ticket.pop(ticket_id, ())):
            del self.comments[comment_id]

    def drop_customer(self, customer_id):
        customer = self.customers.pop(customer_id)
        self._email.pop(customer.email, None)
        self._by_customer.pop(customer_id, None)
