"""The migration runner. See docs/SPEC.md for what every method must do."""
import hashlib
import os
import re
import sqlite3

from .clock import SystemClock, iso
from .errors import (AlreadyApplied, BadArgument, ChecksumMismatch, DuplicateVersion, IrreversibleMigration,
                     MigrationFailed, MissingMigration, OrphanDown, OutOfOrder, UnknownVersion)
from .sql import split_statements

FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.(up|down)\.sql$")


def checksum(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


class Migrator:
    def __init__(self, conn, directory, clock=None):
        self.conn = conn
        self.directory = directory
        self.clock = clock or SystemClock()
        conn.isolation_level = None
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "checksum TEXT NOT NULL, applied_at TEXT NOT NULL, batch INTEGER NOT NULL)")

    # -- reading ---------------------------------------------------------------------------------

    def _scan(self):
        ups, downs = {}, {}
        for fname in sorted(os.listdir(self.directory)):
            m = FILE_RE.match(fname)
            path = os.path.join(self.directory, fname)
            if not m or not os.path.isfile(path):
                continue
            version, name, direction = int(m.group(1)), m.group(2), m.group(3)
            bucket = ups if direction == "up" else downs
            if version in bucket:
                raise DuplicateVersion("two %s files for version %04d" % (direction, version), version)
            bucket[version] = (name, path)
        for version in sorted(downs):
            if version not in ups:
                raise OrphanDown("down file without up file for version %04d" % version, version)
        return ups, downs

    def _applied(self):
        rows = self.conn.execute(
            "SELECT version, name, checksum, applied_at, batch FROM schema_migrations ORDER BY version").fetchall()
        return {r[0]: {"name": r[1], "checksum": r[2], "applied_at": r[3], "batch": r[4]} for r in rows}

    @staticmethod
    def _read(path):
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()

    def _state(self, version, rec, ups):
        if version not in ups:
            return "missing"
        return "applied" if checksum(self._read(ups[version][1])) == rec["checksum"] else "modified"

    # -- public ----------------------------------------------------------------------------------

    def status(self):
        ups, _ = self._scan()
        applied = self._applied()
        out = []
        for version in sorted(set(ups) | set(applied)):
            rec = applied.get(version)
            name = ups[version][0] if version in ups else rec["name"]
            out.append({
                "version": version,
                "name": name,
                "state": "pending" if rec is None else self._state(version, rec, ups),
                "applied_at": rec["applied_at"] if rec else None,
                "batch": rec["batch"] if rec else None,
            })
        return out

    def verify(self):
        ups, _ = self._scan()
        problems = []
        for version, rec in self._applied().items():
            state = self._state(version, rec, ups)
            if state != "applied":
                problems.append({"version": version, "problem": state})
        return problems

    def up(self, target=None, dry_run=False, allow_out_of_order=False):
        ups, _ = self._scan()
        if target is not None and target not in ups:
            raise UnknownVersion("no up file for version %s" % (target,), target)
        applied = self._applied()
        for version, rec in applied.items():
            state = self._state(version, rec, ups)
            if state == "missing":
                raise MissingMigration("applied migration %04d has no up file" % version, version)
            if state == "modified":
                raise ChecksumMismatch("applied migration %04d was modified" % version, version)
        pending = [v for v in sorted(ups) if v not in applied]
        if applied and not allow_out_of_order:
            newest = max(applied)
            older = [v for v in pending if v < newest]
            if older:
                raise OutOfOrder("pending migration %04d is older than applied %04d" % (older[0], newest), older[0])
        todo = [v for v in pending if target is None or v <= target]
        if dry_run or not todo:
            return todo
        batch = max([r["batch"] for r in applied.values()], default=0) + 1
        done = []
        for version in todo:
            name, path = ups[version]
            text = self._read(path)
            self._run(version, text, "INSERT INTO schema_migrations (version, name, checksum, applied_at, batch) "
                      "VALUES (?, ?, ?, ?, ?)",
                      (version, name, checksum(text), iso(self.clock.now()), batch))
            done.append(version)
        return done

    def down(self, steps=None, to=None, last_batch=False, dry_run=False):
        given = [steps is not None, to is not None, bool(last_batch)]
        if sum(given) > 1:
            raise BadArgument("give only one of steps, to, last_batch")
        if steps is not None and (type(steps) is not int or steps < 1):
            raise BadArgument("steps must be an int >= 1")
        if to is not None and (type(to) is not int or to < 0):
            raise BadArgument("to must be an int >= 0")
        if not any(given):
            steps = 1
        ups, downs = self._scan()
        applied = self._applied()
        if to is not None and to != 0 and to not in ups and to not in applied:
            raise UnknownVersion("unknown version %s" % to, to)
        newest_first = sorted(applied, reverse=True)
        if steps is not None:
            chosen = newest_first[:steps]
        elif to is not None:
            chosen = [v for v in newest_first if v > to]
        else:
            top = max([r["batch"] for r in applied.values()], default=None)
            chosen = [v for v in newest_first if applied[v]["batch"] == top]
        for version in chosen:
            if version not in downs:
                raise IrreversibleMigration("migration %04d has no down file" % version, version)
        if dry_run:
            return chosen
        done = []
        for version in chosen:
            self._run(version, self._read(downs[version][1]), "DELETE FROM schema_migrations WHERE version = ?",
                      (version,))
            done.append(version)
        return done

    def stamp(self, version):
        ups, _ = self._scan()
        if version not in ups:
            raise UnknownVersion("no up file for version %s" % (version,), version)
        applied = self._applied()
        if version in applied:
            raise AlreadyApplied("version %04d is already applied" % version, version)
        name, path = ups[version]
        batch = max([r["batch"] for r in applied.values()], default=0) + 1
        self.conn.execute(
            "INSERT INTO schema_migrations (version, name, checksum, applied_at, batch) VALUES (?, ?, ?, ?, ?)",
            (version, name, checksum(self._read(path)), iso(self.clock.now()), batch))

    # -- one migration ---------------------------------------------------------------------------

    def _run(self, version, script, bookkeeping_sql, bookkeeping_args):
        self.conn.execute("BEGIN")
        try:
            for stmt in split_statements(script):
                self.conn.execute(stmt)
            self.conn.execute(bookkeeping_sql, bookkeeping_args)
            self.conn.execute("COMMIT")
        except sqlite3.Error as exc:
            self.conn.execute("ROLLBACK")
            raise MigrationFailed("migration %04d failed: %s" % (version, exc), version, exc) from exc
