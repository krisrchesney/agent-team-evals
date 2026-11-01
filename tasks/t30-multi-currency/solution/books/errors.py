class LedgerError(Exception):
    """Base class. `code` is stable and machine readable; `param` names the offending argument."""
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param


class InvalidAmount(LedgerError):
    code = "invalid_amount"


class InvalidDate(LedgerError):
    code = "invalid_date"


class InvalidAccount(LedgerError):
    code = "invalid_account"


class DuplicateAccount(LedgerError):
    code = "duplicate_account"


class UnknownAccount(LedgerError):
    code = "unknown_account"


class Unbalanced(LedgerError):
    code = "unbalanced"


class UnknownEntry(LedgerError):
    code = "unknown_entry"


class UnknownInvoice(LedgerError):
    code = "unknown_invoice"


class InvoiceError(LedgerError):
    code = "invoice_error"


class BudgetError(LedgerError):
    code = "budget_error"


class RecurringError(LedgerError):
    code = "recurring_error"


class UnknownCurrency(LedgerError):
    code = "unknown_currency"


class CurrencyMismatch(LedgerError):
    code = "currency_mismatch"


class InvalidRate(LedgerError):
    code = "invalid_rate"


class NoRate(LedgerError):
    code = "no_rate"
