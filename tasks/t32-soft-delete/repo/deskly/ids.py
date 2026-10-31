class Ids:
    """c1, c2... for customers, t1... for tickets, m1... for comments. A number is never used twice."""

    def __init__(self):
        self.counters = {}

    def new(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}{n}"
