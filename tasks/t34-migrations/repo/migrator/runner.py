"""The migration runner. See docs/SPEC.md for what every method must do."""
from .clock import SystemClock


class Migrator:
    def __init__(self, conn, directory, clock=None):
        self.conn = conn
        self.directory = directory
        self.clock = clock or SystemClock()
        raise NotImplementedError("see docs/SPEC.md")

    def status(self):
        raise NotImplementedError

    def verify(self):
        raise NotImplementedError

    def up(self, target=None, dry_run=False, allow_out_of_order=False):
        raise NotImplementedError

    def down(self, steps=None, to=None, last_batch=False, dry_run=False):
        raise NotImplementedError

    def stamp(self, version):
        raise NotImplementedError
