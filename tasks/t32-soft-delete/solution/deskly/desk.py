from . import comments, customers, exporter, reports, snapshot, tickets, trash
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

    def get_customer(self, customer_id, include_deleted=False):
        return customers.get(self, customer_id, include_deleted)

    def find_customer(self, email):
        return customers.find_by_email(self, email)

    def list_customers(self, limit=None, include_deleted=False):
        return customers.list_(self, limit, include_deleted)

    def update_customer(self, customer_id, name=None, email=None):
        return customers.update(self, customer_id, name, email)

    def delete_customer(self, customer_id):
        return customers.delete(self, customer_id)

    def restore_customer(self, customer_id):
        return customers.restore(self, customer_id)

    def merge_customers(self, keep, drop):
        return customers.merge(self, keep, drop)

    # tickets

    def open_ticket(self, customer, subject, body, priority=2, tags=()):
        return tickets.open_(self, customer, subject, body, priority, tags)

    def get_ticket(self, ticket_id, include_deleted=False):
        return tickets.get(self, ticket_id, include_deleted)

    def list_tickets(self, customer=None, status=None, tag=None, limit=None, include_deleted=False):
        return tickets.list_(self, customer, status, tag, limit, include_deleted)

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

    def restore_ticket(self, ticket_id):
        return tickets.restore(self, ticket_id)

    # comments

    def add_comment(self, ticket, author, text):
        return comments.add(self, ticket, author, text)

    def list_comments(self, ticket, limit=None, include_deleted=False):
        return comments.list_(self, ticket, limit, include_deleted)

    def delete_comment(self, comment_id):
        return comments.delete(self, comment_id)

    def restore_comment(self, comment_id):
        return comments.restore(self, comment_id)

    # trash

    def trash(self, kind=None, limit=None):
        return trash.listing(self, kind, limit)

    def purge(self, kind, row_id):
        return trash.purge(self, kind, row_id)

    def purge_expired(self):
        return trash.purge_expired(self)

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

    def tickets_csv(self, include_deleted=False):
        return exporter.tickets_csv(self, include_deleted)

    def customers_csv(self, include_deleted=False):
        return exporter.customers_csv(self, include_deleted)

    # persistence

    def dump(self):
        return snapshot.dump(self)

    @classmethod
    def load(cls, data, clock=None):
        desk = cls(clock)
        snapshot.load(data, desk)
        return desk
