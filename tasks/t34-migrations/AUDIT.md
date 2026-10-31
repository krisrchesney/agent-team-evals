# t34-migrations: where each hidden-test rule is shown

Every rule is written in `repo/docs/SPEC.md` (the prompt points to it). This file is outside `repo/`,
so agents never see it. Nothing here depends on a value the spec does not give.

| Test group | Rule | SPEC.md section |
|---|---|---|
| `TestSetup` | tracking table columns, `isolation_level = None`, creation is idempotent, empty directory | Tracking table |
| `test_ignores_non_matching_names` | exact name pattern; near-misses and directories ignored | Files |
| `test_orders_by_integer_value_with_gaps` | order by integer value | Files |
| `test_duplicate_*`, `test_orphan_down`, `test_errors_are_migration_errors` | `DuplicateVersion`, `OrphanDown`, `version` set | Files; `errors.py` |
| `test_directory_is_read_on_every_call` | re-scan on every public call | Files |
| `TestUp` basics, `test_second_up_is_a_noop_without_a_batch` | applied versions returned, `applied_at` from clock, batch = highest + 1, no batch when nothing applied | `up` step 7, Tracking table |
| `test_target`, `test_unknown_target` | `<= target`, target without up file is `UnknownVersion` (including `0`) | `up` steps 2 and 5 |
| `test_dry_run_changes_nothing` | dry run returns the list, changes nothing | `up` step 6 |
| `test_multi_statement_file_with_trigger`, `test_comment_only_migration_is_recorded` | statements via `split_statements`; a comment-only file still counts as applied | Running one migration; `sql.py` |
| `TestFailure` | one transaction per migration, rollback of only that one, `MigrationFailed` with `version` and `cause`, nothing after it runs; a failed down keeps the record | Running one migration |
| `TestChecksums` normalisation tests | CRLF, lone CR, trailing blanks and trailing whitespace are ignored; indentation, comments and inner blank lines count | Checksum |
| `test_up_refuses_*`, `test_lowest_problem_wins` | `MissingMigration` / `ChecksumMismatch` with `version`; version order decides which raises | `up` step 3 |
| `test_status_and_verify_*`, `test_status_name_prefers_the_file`, `TestStatus` | states, name source, `applied_at`/`batch` None for pending, verify list shape | `status`, `verify` |
| `test_down_ignores_checksums` | down does not compare checksums | `down` Checks |
| `TestOrdering` | `OutOfOrder` for lowest pending below the highest applied, `allow_out_of_order`, step 3 before step 4, target does not filter the order check, dry run still raises | `up` steps 3 to 6 |
| `TestDown` | default one step; `steps`, `to`, `last_batch` selectors; `to=0`; unknown `to`; `BadArgument` cases (bool, float, str, negatives, two selectors); irreversible reports the highest version and changes nothing; dry run keeps the check; batch numbering after a down | `down` |
| `TestStamp` | no SQL run, new batch, errors, no order check | `stamp` |

What makes it hard: the spec is long (about 120 lines) and its rules interact. The order of the checks
in `up` (missing/modified before out-of-order before target filtering), all-or-nothing irreversibility
checks in `down`, checksum normalisation details, batch numbering across `up`, `down` and `stamp`, and
per-migration transactions (so `executescript` is the wrong tool and the connection must stay usable after
a failure). A reader who skims the spec will miss several of these; each is stated once.
