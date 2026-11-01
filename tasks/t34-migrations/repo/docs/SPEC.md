# Migrator spec

`Migrator(conn, directory, clock=None)` runs SQL migration files from `directory` against an open
`sqlite3.Connection`. `clock.now()` gives the time (default `SystemClock`).

## Files

A migration is one or two files in `directory` (not subfolders):

- `<version>_<name>.up.sql` applies it, `<version>_<name>.down.sql` reverts it.
- `<version>` is exactly four digits. `<name>` is lowercase letters, digits and underscores.
- The integer value of the version orders migrations (`0010` after `0002`). Gaps are fine.
- Any other file name in the directory is ignored, including names that nearly match
  (`1_x.up.sql`, `0001_X.up.sql`, `0001_x.sql`, `0001_x.up.sql.bak`).
- The directory is read again at the start of every public method, so files added or edited
  between calls are seen.
- Two up files with the same version raise `DuplicateVersion` (`version` set). So do two down files.
- A down file whose version has no up file raises `OrphanDown`.
- A migration with no down file is *irreversible*.
- Files are read as UTF-8.

## Tracking table

The constructor does `conn.isolation_level = None` (so the runner owns transactions) and creates, if
missing, the table

    schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL,
                      applied_at TEXT NOT NULL, batch INTEGER NOT NULL)

`applied_at` is the `clock.iso` format of `clock.now()`. `name` is the file's name part.

## Checksum

SHA-256 hex digest of the up file's text after normalizing: `\r\n` and lone `\r` become `\n`, trailing
spaces and tabs are removed from every line, and leading and trailing blank lines are removed. The
result is encoded as UTF-8. Comments count. So a file that is only re-saved with CRLF line endings, or
with trailing whitespace added, has the same checksum; changing any SQL or comment text changes it.

## Running one migration

A migration runs in a single transaction: `BEGIN`, each statement from `sql.split_statements` in order,
the change to `schema_migrations` (insert on up, delete on down), `COMMIT`. If a statement raises
(`sqlite3.Error`), the transaction is rolled back (so the schema and the table are unchanged by that
migration) and `MigrationFailed` is raised with `version` and `cause` set. Migrations that finished
earlier in the same call stay applied, and nothing after the failed one is attempted.

## Methods

### `status()`
Returns a list of dicts, ascending by version, one per version known from up files or from the table:

    {"version": int, "name": str, "state": ..., "applied_at": str|None, "batch": int|None}

`state` is `"pending"` (up file, not applied), `"applied"` (applied, up file present, checksum
matches), `"modified"` (applied, up file present, checksum differs) or `"missing"` (applied, no up
file). `name` is the up file's name part when the file exists, else the recorded name. `applied_at` and
`batch` come from the table, `None` for pending.

### `verify()`
Returns a list of `{"version": int, "problem": "missing" | "modified"}`, ascending by version, for
every applied migration whose state is missing or modified. Empty list when all is well. It does not
raise for those problems (it still raises `DuplicateVersion` / `OrphanDown` from reading the directory).

### `up(target=None, dry_run=False, allow_out_of_order=False)`
Applies pending migrations in ascending version order and returns the list of versions applied.
Order of work:

1. Read the directory (errors above).
2. If `target` is not `None` and has no up file, raise `UnknownVersion`.
3. Check applied migrations, ascending: the first one that is missing raises `MissingMigration`; the
   first one that is modified raises `ChecksumMismatch` (both set `version`). Migrations are checked
   in version order and the first problem found raises, so a missing migration with a lower version
   wins over a modified one with a higher version, and the other way round.
4. Unless `allow_out_of_order`, if any pending migration has a version lower than the highest applied
   version, raise `OutOfOrder` with `version` of the lowest such pending migration.
5. The list to apply is every pending migration with version <= `target` (all, if `target` is `None`).
   A target that is already applied, or lower than everything pending, gives an empty list.
6. With `dry_run=True`, return that list and change nothing.
7. Otherwise apply them one by one. All migrations applied by one call share a `batch` number: the
   highest batch in the table plus one (1 for an empty table). A call that applies nothing uses no
   batch number.

### `down(steps=None, to=None, last_batch=False, dry_run=False)`
Reverts applied migrations, newest version first, and returns the reverted versions in the order they
were reverted. Exactly one selector may be given; with none, `steps=1`.

- `steps=n`: the `n` highest applied versions (fewer if fewer are applied). `n` must be an `int`
  (not a `bool`) >= 1.
- `to=v`: every applied version greater than `v`. `v` must be `0` or a version that is known (it has an
  up file or is in the table), else `UnknownVersion`.
- `last_batch=True`: every migration whose batch equals the highest batch in the table.
- More than one selector, or a bad value, raises `BadArgument` before anything else happens.

Checks, before any change: every migration chosen must have a down file. If some do not, raise
`IrreversibleMigration` with `version` of the *highest* such version, and revert nothing. Down does not
compare checksums (an edited up file does not block a rollback). Reading the directory still raises its
own errors. With `dry_run=True` return the list and change nothing (the irreversibility check still
applies). Nothing applied means an empty list.

### `stamp(version)`
Records an up file's migration as applied without running any SQL. Raises `UnknownVersion` if there is
no up file for `version`, `AlreadyApplied` if it is in the table. Stores the current checksum, the
file's name part, the time, and a new batch number (highest + 1). Returns `None`. `stamp` does not run
the order or checksum checks of `up`.
