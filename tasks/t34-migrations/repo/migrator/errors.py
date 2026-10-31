"""Every error the runner raises. `version` is the migration the error is about, when there is one."""


class MigrationError(Exception):
    def __init__(self, message, version=None):
        super().__init__(message)
        self.version = version


class BadArgument(MigrationError):
    """A method was called with arguments the spec does not allow."""


class DuplicateVersion(MigrationError):
    """Two files in one direction share a version."""


class OrphanDown(MigrationError):
    """A down file exists for a version that has no up file."""


class UnknownVersion(MigrationError):
    """A version that is not known to the runner was named."""


class AlreadyApplied(MigrationError):
    """The version is already recorded as applied."""


class ChecksumMismatch(MigrationError):
    """An applied migration's up file has changed since it was applied."""


class MissingMigration(MigrationError):
    """An applied migration's up file is gone."""


class OutOfOrder(MigrationError):
    """A pending migration is older than the newest applied one."""


class IrreversibleMigration(MigrationError):
    """A migration that must be reverted has no down file."""


class MigrationFailed(MigrationError):
    """A migration's SQL raised. `cause` is the original exception."""

    def __init__(self, message, version=None, cause=None):
        super().__init__(message, version)
        self.cause = cause
