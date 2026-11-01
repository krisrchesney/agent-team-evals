class Ids:
    """p1, p2... for projects, t1... for tasks, c1... for comments, u1... for members."""

    def __init__(self):
        self.counters = {}

    def new(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}{n}"
