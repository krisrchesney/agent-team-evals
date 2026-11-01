"""Hidden tests for t34-migrations. Every rule is in docs/SPEC.md; see AUDIT.md."""
import os
import sqlite3
import tempfile
import unittest

from migrator import FixedClock, Migrator
from migrator.errors import (AlreadyApplied, BadArgument, ChecksumMismatch, DuplicateVersion, IrreversibleMigration,
                             MigrationError, MigrationFailed, MissingMigration, OrphanDown, OutOfOrder,
                             UnknownVersion)

CREATE_USERS = "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);\n"
ADD_NAME = "ALTER TABLE users ADD COLUMN name TEXT;\n"
CREATE_POSTS = "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER);\n"


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = os.path.join(self._tmp.name, "migrations")
        os.mkdir(self.dir)
        self.conn = sqlite3.connect(":memory:")
        self.clock = FixedClock()

    def write(self, fname, text, raw=False):
        with open(os.path.join(self.dir, fname), "wb") as fh:
            fh.write(text if raw else text.encode("utf-8"))

    def remove(self, fname):
        os.remove(os.path.join(self.dir, fname))

    def standard(self):
        self.write("0001_create_users.up.sql", CREATE_USERS)
        self.write("0001_create_users.down.sql", "DROP TABLE users;\n")
        self.write("0002_add_name.up.sql", ADD_NAME)
        self.write("0002_add_name.down.sql", "ALTER TABLE users DROP COLUMN name;\n")
        self.write("0003_create_posts.up.sql", CREATE_POSTS)
        self.write("0003_create_posts.down.sql", "DROP TABLE posts;\n")

    def m(self):
        return Migrator(self.conn, self.dir, clock=self.clock)

    def tables(self):
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'schema_migrations'")
        return sorted(r[0] for r in rows)

    def columns(self, table):
        return [r[1] for r in self.conn.execute("PRAGMA table_info(%s)" % table)]

    def rows(self):
        return self.conn.execute("SELECT version, name, applied_at, batch FROM schema_migrations ORDER BY version").fetchall()

    def versions(self):
        return [r[0] for r in self.rows()]


class TestSetup(Base):
    def test_constructor_creates_tracking_table_and_manual_transactions(self):
        self.m()
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(schema_migrations)")]
        self.assertEqual(cols, ["version", "name", "checksum", "applied_at", "batch"])
        self.assertIsNone(self.conn.isolation_level)

    def test_constructor_is_idempotent(self):
        self.m()
        self.m()
        self.assertEqual(self.m().status(), [])

    def test_empty_directory(self):
        m = self.m()
        self.assertEqual(m.up(), [])
        self.assertEqual(m.status(), [])
        self.assertEqual(m.down(), [])


class TestDiscovery(Base):
    def test_ignores_non_matching_names(self):
        self.standard()
        for junk in ("1_x.up.sql", "0004_X.up.sql", "0004_x.sql", "0004_x.up.sql.bak", "00004_x.up.sql", "README.md",
                     "0004_x-y.up.sql"):
            self.write(junk, "THIS IS NOT SQL;\n")
        os.mkdir(os.path.join(self.dir, "0009_dir.up.sql"))
        self.assertEqual(self.m().up(), [1, 2, 3])

    def test_orders_by_integer_value_with_gaps(self):
        self.write("0010_c.up.sql", "CREATE TABLE c (id INTEGER);")
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        self.write("0100_d.up.sql", "CREATE TABLE d (id INTEGER);")
        self.assertEqual(self.m().up(), [2, 10, 100])
        self.assertEqual(self.tables(), ["b", "c", "d"])

    def test_duplicate_up_version(self):
        self.write("0001_a.up.sql", "SELECT 1;")
        self.write("0001_b.up.sql", "SELECT 2;")
        with self.assertRaises(DuplicateVersion) as ctx:
            self.m().up()
        self.assertEqual(ctx.exception.version, 1)

    def test_duplicate_down_version(self):
        self.write("0001_a.up.sql", "SELECT 1;")
        self.write("0001_a.down.sql", "SELECT 1;")
        self.write("0001_b.down.sql", "SELECT 2;")
        with self.assertRaises(DuplicateVersion):
            self.m().status()

    def test_orphan_down(self):
        self.write("0001_a.up.sql", "SELECT 1;")
        self.write("0002_b.down.sql", "SELECT 1;")
        with self.assertRaises(OrphanDown) as ctx:
            self.m().verify()
        self.assertEqual(ctx.exception.version, 2)

    def test_directory_is_read_on_every_call(self):
        m = self.m()
        self.write("0001_create_users.up.sql", CREATE_USERS)
        self.assertEqual(m.up(), [1])
        self.write("0002_add_name.up.sql", ADD_NAME)
        self.assertEqual(m.up(), [2])

    def test_errors_are_migration_errors(self):
        self.write("0001_a.up.sql", "SELECT 1;")
        self.write("0001_b.up.sql", "SELECT 2;")
        with self.assertRaises(MigrationError):
            self.m().up()


class TestUp(Base):
    def test_applies_all_in_order_and_records(self):
        self.standard()
        self.assertEqual(self.m().up(), [1, 2, 3])
        self.assertEqual(self.tables(), ["posts", "users"])
        self.assertEqual(self.columns("users"), ["id", "email", "name"])
        self.assertEqual(self.rows(), [(1, "create_users", "2026-03-02T08:00:00Z", 1),
                                       (2, "add_name", "2026-03-02T08:00:00Z", 1),
                                       (3, "create_posts", "2026-03-02T08:00:00Z", 1)])

    def test_second_up_is_a_noop_without_a_batch(self):
        self.standard()
        m = self.m()
        m.up()
        self.clock.advance(hours=1)
        self.assertEqual(m.up(), [])
        self.write("0004_more.up.sql", "CREATE TABLE more (id INTEGER);")
        self.assertEqual(m.up(), [4])
        self.assertEqual([r[3] for r in self.rows()], [1, 1, 1, 2])
        self.assertEqual(self.rows()[3][2], "2026-03-02T09:00:00Z")

    def test_target(self):
        self.standard()
        m = self.m()
        self.assertEqual(m.up(target=2), [1, 2])
        self.assertEqual(self.tables(), ["users"])
        self.assertEqual(m.up(target=2), [])
        self.assertEqual(m.up(target=1), [])
        self.assertEqual(m.up(target=3), [3])
        self.assertEqual([r[3] for r in self.rows()], [1, 1, 2])

    def test_unknown_target(self):
        self.standard()
        m = self.m()
        for bad in (4, 0):
            with self.assertRaises(UnknownVersion) as ctx:
                m.up(target=bad)
            self.assertEqual(ctx.exception.version, bad)
        self.assertEqual(self.versions(), [])

    def test_dry_run_changes_nothing(self):
        self.standard()
        m = self.m()
        self.assertEqual(m.up(dry_run=True), [1, 2, 3])
        self.assertEqual(m.up(target=2, dry_run=True), [1, 2])
        self.assertEqual(self.tables(), [])
        self.assertEqual(self.versions(), [])
        m.up(target=1)
        self.assertEqual(m.up(dry_run=True), [2, 3])
        self.assertEqual(self.versions(), [1])

    def test_multi_statement_file_with_trigger(self):
        self.write("0001_a.up.sql", "-- audit\nCREATE TABLE a (id INTEGER);\nCREATE TABLE log (n INTEGER);\n"
                                    "CREATE TRIGGER t AFTER INSERT ON a BEGIN\n  INSERT INTO log VALUES (1);\nEND;\n")
        self.m().up()
        self.conn.execute("INSERT INTO a VALUES (5)")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM log").fetchone()[0], 1)

    def test_comment_only_migration_is_recorded(self):
        self.write("0001_noop.up.sql", "-- nothing yet\n")
        self.assertEqual(self.m().up(), [1])
        self.assertEqual(self.versions(), [1])


class TestFailure(Base):
    def broken(self):
        self.write("0001_create_users.up.sql", CREATE_USERS)
        self.write("0002_broken.up.sql", "CREATE TABLE t1 (id INTEGER);\nINSERT INTO nope VALUES (1);\n")
        self.write("0003_create_posts.up.sql", CREATE_POSTS)

    def test_failed_migration_rolls_back_only_itself(self):
        self.broken()
        with self.assertRaises(MigrationFailed) as ctx:
            self.m().up()
        self.assertEqual(ctx.exception.version, 2)
        self.assertIsInstance(ctx.exception.cause, sqlite3.Error)
        self.assertEqual(self.tables(), ["users"])
        self.assertEqual(self.versions(), [1])

    def test_failure_does_not_attempt_later_migrations(self):
        self.broken()
        with self.assertRaises(MigrationFailed):
            self.m().up()
        self.assertNotIn("posts", self.tables())

    def test_connection_is_usable_after_failure_and_retry_works(self):
        self.broken()
        m = self.m()
        with self.assertRaises(MigrationFailed):
            m.up()
        self.write("0002_broken.up.sql", "CREATE TABLE t1 (id INTEGER);\n")
        self.assertEqual(m.up(), [2, 3])
        self.assertEqual(self.tables(), ["posts", "t1", "users"])
        self.assertEqual([r[3] for r in self.rows()], [1, 2, 2])

    def test_failed_down_rolls_back_and_keeps_record(self):
        self.write("0001_a.up.sql", CREATE_USERS)
        self.write("0001_a.down.sql", "DROP TABLE users;\nDROP TABLE missing_table;\n")
        m = self.m()
        m.up()
        with self.assertRaises(MigrationFailed) as ctx:
            m.down()
        self.assertEqual(ctx.exception.version, 1)
        self.assertEqual(self.tables(), ["users"])
        self.assertEqual(self.versions(), [1])


class TestChecksums(Base):
    def applied(self):
        self.write("0001_create_users.up.sql", CREATE_USERS)
        self.write("0002_add_name.up.sql", ADD_NAME)
        m = self.m()
        m.up()
        return m

    def test_status_applied(self):
        m = self.applied()
        self.assertEqual([s["state"] for s in m.status()], ["applied", "applied"])
        self.assertEqual(m.verify(), [])

    def test_crlf_and_trailing_whitespace_do_not_change_checksum(self):
        m = self.applied()
        self.write("0001_create_users.up.sql",
                   "\r\n\r\nCREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);   \r\n\r\n\r\n", raw=False)
        self.write("0002_add_name.up.sql", "ALTER TABLE users ADD COLUMN name TEXT;\t\r", raw=False)
        self.assertEqual([s["state"] for s in m.status()], ["applied", "applied"])
        self.assertEqual(m.up(), [])

    def test_lone_cr_line_endings_normalize(self):
        self.write("0001_a.up.sql", "-- one\nCREATE TABLE a (id INTEGER);\n")
        m = self.m()
        m.up()
        self.write("0001_a.up.sql", b"-- one\rCREATE TABLE a (id INTEGER);\r", raw=True)
        self.assertEqual(m.verify(), [])

    def test_leading_indentation_and_comments_count(self):
        m = self.applied()
        self.write("0001_create_users.up.sql", "  " + CREATE_USERS)
        self.assertEqual(m.verify(), [{"version": 1, "problem": "modified"}])
        self.write("0001_create_users.up.sql", CREATE_USERS)
        self.write("0002_add_name.up.sql", "-- note\n" + ADD_NAME)
        self.assertEqual(m.verify(), [{"version": 2, "problem": "modified"}])

    def test_inner_blank_lines_count(self):
        m = self.applied()
        self.write("0001_create_users.up.sql", "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);\n\n-- x\n")
        self.assertEqual(m.verify(), [{"version": 1, "problem": "modified"}])

    def test_up_refuses_modified(self):
        m = self.applied()
        self.write("0002_add_name.up.sql", "ALTER TABLE users ADD COLUMN nickname TEXT;\n")
        self.write("0003_create_posts.up.sql", CREATE_POSTS)
        with self.assertRaises(ChecksumMismatch) as ctx:
            m.up()
        self.assertEqual(ctx.exception.version, 2)
        self.assertEqual(self.versions(), [1, 2])

    def test_up_refuses_missing(self):
        m = self.applied()
        self.remove("0001_create_users.up.sql")
        with self.assertRaises(MissingMigration) as ctx:
            m.up()
        self.assertEqual(ctx.exception.version, 1)

    def test_lowest_problem_wins(self):
        m = self.applied()
        self.remove("0002_add_name.up.sql")
        self.write("0001_create_users.up.sql", "CREATE TABLE users (id INTEGER);\n")
        with self.assertRaises(ChecksumMismatch):
            m.up()
        self.write("0001_create_users.up.sql", CREATE_USERS)
        with self.assertRaises(MissingMigration):
            m.up()
        self.write("0002_add_name.up.sql", "SELECT 1;\n")
        self.remove("0001_create_users.up.sql")
        with self.assertRaises(MissingMigration) as ctx:
            m.up()
        self.assertEqual(ctx.exception.version, 1)

    def test_status_and_verify_report_modified_and_missing(self):
        m = self.applied()
        self.write("0001_create_users.up.sql", "CREATE TABLE users (id INTEGER);\n")
        self.remove("0002_add_name.up.sql")
        self.write("0003_pending.up.sql", "SELECT 1;")
        st = m.status()
        self.assertEqual([(s["version"], s["state"]) for s in st], [(1, "modified"), (2, "missing"), (3, "pending")])
        self.assertEqual(st[1]["name"], "add_name")
        self.assertEqual(m.verify(), [{"version": 1, "problem": "modified"}, {"version": 2, "problem": "missing"}])

    def test_down_ignores_checksums(self):
        m = self.applied()
        self.write("0002_add_name.down.sql", "ALTER TABLE users DROP COLUMN name;\n")
        self.write("0002_add_name.up.sql", "SELECT 'edited';\n")
        self.assertEqual(m.down(), [2])
        self.assertEqual(self.versions(), [1])

    def test_status_name_prefers_the_file(self):
        m = self.applied()
        self.remove("0001_create_users.up.sql")
        self.write("0001_make_users.up.sql", CREATE_USERS)
        self.assertEqual(m.status()[0]["name"], "make_users")
        self.assertEqual(m.status()[0]["state"], "applied")


class TestOrdering(Base):
    def test_out_of_order_pending_is_refused(self):
        self.write("0001_a.up.sql", "CREATE TABLE a (id INTEGER);")
        self.write("0003_c.up.sql", "CREATE TABLE c (id INTEGER);")
        m = self.m()
        m.up()
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        self.write("0000_z.up.sql", "CREATE TABLE z (id INTEGER);")
        self.write("0004_d.up.sql", "CREATE TABLE d (id INTEGER);")
        with self.assertRaises(OutOfOrder) as ctx:
            m.up()
        self.assertEqual(ctx.exception.version, 0)
        self.assertEqual(self.tables(), ["a", "c"])

    def test_out_of_order_allowed(self):
        self.write("0001_a.up.sql", "CREATE TABLE a (id INTEGER);")
        self.write("0003_c.up.sql", "CREATE TABLE c (id INTEGER);")
        m = self.m()
        m.up()
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        self.write("0004_d.up.sql", "CREATE TABLE d (id INTEGER);")
        self.assertEqual(m.up(allow_out_of_order=True), [2, 4])
        self.assertEqual(self.versions(), [1, 2, 3, 4])

    def test_checksum_check_comes_before_order_check(self):
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        m = self.m()
        m.up()
        self.write("0001_a.up.sql", "CREATE TABLE a (id INTEGER);")
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER, x INTEGER);")
        with self.assertRaises(ChecksumMismatch):
            m.up()

    def test_target_does_not_hide_an_out_of_order_migration(self):
        self.write("0005_e.up.sql", "CREATE TABLE e (id INTEGER);")
        m = self.m()
        m.up()
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        self.write("0006_f.up.sql", "CREATE TABLE f (id INTEGER);")
        with self.assertRaises(OutOfOrder):
            m.up(target=6)

    def test_dry_run_still_raises(self):
        self.write("0005_e.up.sql", "CREATE TABLE e (id INTEGER);")
        m = self.m()
        m.up()
        self.write("0002_b.up.sql", "CREATE TABLE b (id INTEGER);")
        with self.assertRaises(OutOfOrder):
            m.up(dry_run=True)
        self.assertEqual(m.up(dry_run=True, allow_out_of_order=True), [2])


class TestDown(Base):
    def test_default_is_one_step(self):
        self.standard()
        m = self.m()
        m.up()
        self.assertEqual(m.down(), [3])
        self.assertEqual(self.tables(), ["users"])
        self.assertEqual(self.versions(), [1, 2])

    def test_steps(self):
        self.standard()
        m = self.m()
        m.up()
        self.assertEqual(m.down(steps=2), [3, 2])
        self.assertEqual(self.columns("users"), ["id", "email"])
        self.assertEqual(m.down(steps=10), [1])
        self.assertEqual(self.tables(), [])

    def test_to(self):
        self.standard()
        m = self.m()
        m.up()
        self.assertEqual(m.down(to=1), [3, 2])
        self.assertEqual(m.down(to=1), [])
        self.assertEqual(m.down(to=0), [1])
        self.assertEqual(self.versions(), [])

    def test_to_unknown_version(self):
        self.standard()
        m = self.m()
        m.up()
        with self.assertRaises(UnknownVersion):
            m.down(to=7)
        self.assertEqual(self.versions(), [1, 2, 3])

    def test_last_batch(self):
        self.standard()
        m = self.m()
        m.up(target=1)
        m.up()
        self.assertEqual(m.down(last_batch=True), [3, 2])
        self.assertEqual(self.versions(), [1])
        self.assertEqual(m.down(last_batch=True), [1])
        self.assertEqual(m.down(last_batch=True), [])

    def test_batch_numbers_continue_after_down(self):
        self.standard()
        m = self.m()
        m.up(target=2)
        m.down()
        m.up()
        self.assertEqual([r[3] for r in self.rows()], [1, 2, 2])
        self.assertEqual(self.versions(), [1, 2, 3])

    def test_bad_arguments(self):
        self.standard()
        m = self.m()
        m.up()
        for kwargs in ({"steps": 0}, {"steps": -1}, {"steps": 1.0}, {"steps": True}, {"steps": "2"}, {"to": -1},
                       {"to": "1"}, {"steps": 1, "to": 1}, {"steps": 1, "last_batch": True},
                       {"to": 1, "last_batch": True}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(BadArgument):
                    m.down(**kwargs)
        self.assertEqual(self.versions(), [1, 2, 3])

    def test_irreversible_reports_highest_and_changes_nothing(self):
        self.standard()
        self.remove("0001_create_users.down.sql")
        self.remove("0002_add_name.down.sql")
        m = self.m()
        m.up()
        with self.assertRaises(IrreversibleMigration) as ctx:
            m.down(steps=3)
        self.assertEqual(ctx.exception.version, 2)
        self.assertEqual(self.versions(), [1, 2, 3])
        self.assertEqual(self.tables(), ["posts", "users"])
        self.assertEqual(m.down(), [3])

    def test_dry_run(self):
        self.standard()
        m = self.m()
        m.up()
        self.assertEqual(m.down(steps=2, dry_run=True), [3, 2])
        self.assertEqual(self.versions(), [1, 2, 3])
        self.remove("0003_create_posts.down.sql")
        with self.assertRaises(IrreversibleMigration):
            m.down(dry_run=True)

    def test_down_on_nothing_applied(self):
        self.standard()
        self.assertEqual(self.m().down(steps=3), [])

    def test_down_then_up_round_trip(self):
        self.standard()
        m = self.m()
        m.up()
        m.down(to=0)
        self.assertEqual(self.tables(), [])
        self.assertEqual(m.up(), [1, 2, 3])


class TestStamp(Base):
    def test_stamp_records_without_running(self):
        self.standard()
        m = self.m()
        self.assertIsNone(m.stamp(1))
        self.assertEqual(self.tables(), [])
        self.assertEqual(self.rows(), [(1, "create_users", "2026-03-02T08:00:00Z", 1)])
        self.assertEqual([s["state"] for s in m.status()], ["applied", "pending", "pending"])

    def test_stamp_errors(self):
        self.standard()
        m = self.m()
        m.stamp(1)
        with self.assertRaises(AlreadyApplied):
            m.stamp(1)
        with self.assertRaises(UnknownVersion):
            m.stamp(9)

    def test_stamp_takes_the_next_batch_and_up_continues(self):
        self.standard()
        m = self.m()
        m.stamp(1)
        m.stamp(2)
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, name TEXT)")
        self.assertEqual(m.up(), [3])
        self.assertEqual([r[3] for r in self.rows()], [1, 2, 3])

    def test_stamp_does_not_check_order(self):
        self.standard()
        m = self.m()
        m.stamp(3)
        m.stamp(1)
        with self.assertRaises(OutOfOrder):
            m.up()


class TestStatus(Base):
    def test_status_shape(self):
        self.standard()
        m = self.m()
        m.up(target=2)
        self.clock.advance(minutes=30)
        st = m.status()
        self.assertEqual(st[0], {"version": 1, "name": "create_users", "state": "applied",
                                 "applied_at": "2026-03-02T08:00:00Z", "batch": 1})
        self.assertEqual(st[2], {"version": 3, "name": "create_posts", "state": "pending",
                                 "applied_at": None, "batch": None})
        self.assertEqual([s["version"] for s in st], [1, 2, 3])

    def test_status_includes_missing_only_in_table(self):
        self.standard()
        m = self.m()
        m.up()
        for f in ("0002_add_name.up.sql", "0002_add_name.down.sql"):
            self.remove(f)
        self.assertEqual([(s["version"], s["state"]) for s in m.status()], [(1, "applied"), (2, "missing"), (3, "applied")])


if __name__ == "__main__":
    unittest.main()
