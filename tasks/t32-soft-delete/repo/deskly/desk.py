from . import comments, customers, exporter, reports, snapshot, tickets
from .activity import Feed
from .clock import SystemClock
from .ids import Ids
from .search import SearchIndex
from .store import Store


class Desk:
    """The whole service. Every method returns plain data."""

    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.store = Store()
        self.ids = Ids()
        self.feed = Feed(self.clock)
        self.search = SearchIndex(self.store)

    # customers

    def create_customer(self, name, email):
        return customers.create(self, name, email)

    def get_customer(self, customer_id):
        return customers.get(self, customer_id)

    def find_customer(self, email):
        return customers.find_by_email(self, email)

    def list_customers(self, limit=None):
        return customers.list_(self, limit)

    def update_customer(self, customer_id, name=None, email=None):
        return customers.update(self, customer_id, name, email)

    def delete_customer(self, customer_id):
        return customers.delete(self, customer_id)

    def merge_customers(self, keep, drop):
        return customers.merge(self, keep, drop)

    # tickets

    def open_ticket(self, customer, subject, body, priority=2, tags=()):
        return tickets.open_(self, customer, subject, body, priority, tags)

    def get_ticket(self, ticket_id):
        return tickets.get(self, ticket_id)

    def list_tickets(self, customer=None, status=None, tag=None, limit=None):
        return tickets.list_(self, customer, status, tag, limit)

    def set_status(self, ticket_id, status):
        return tickets.set_status(self, ticket_id, status)

    def add_tag(self, ticket_id, tag):
        return tickets.add_tag(self, ticket_id, tag)

    def remove_tag(self, ticket_id, tag):
        return tickets.remove_tag(self, ticket_id, tag)

    def rename_tag(self, old, new):
        return tickets.rename_tag(self, old, new)

    def delete_ticket(self, ticket_id):
        return tickets.delete(self, ticket_id)

    # comments

    def add_comment(self, ticket, author, text):
        return comments.add(self, ticket, author, text)

    def list_comments(self, ticket, limit=None):
        return comments.list_(self, ticket, limit)

    def delete_comment(self, comment_id):
        return comments.delete(self, comment_id)

    # search, reports, feed, exports

    def search_tickets(self, text, limit=10):
        return self.search.query(text, limit)

    def status_counts(self):
        return reports.status_counts(self)

    def tag_counts(self):
        return reports.tag_counts(self)

    def customer_summary(self, customer):
        return reports.customer_summary(self, customer)

    def aging(self):
        return reports.aging(self)

    def busiest_customers(self, limit=3):
        return reports.busiest_customers(self, limit)

    def stats(self):
        return reports.stats(self)

    def activity(self, limit=20):
        return self.feed.recent(limit)

    def tickets_csv(self):
        return exporter.tickets_csv(self)

    def customers_csv(self):
        return exporter.customers_csv(self)

    # persistence

    def dump(self):
        return snapshot.dump(self)

    @classmethod
    def load(cls, data, clock=None):
        desk = cls(clock)
        snapshot.load(data, desk)
        return desk
