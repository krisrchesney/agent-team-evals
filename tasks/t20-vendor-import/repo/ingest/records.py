"""The normalized output of every importer."""
import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class InvoiceLine:
    vendor: str
    invoice_id: str
    line_no: int
    sku: str
    description: str
    qty: int
    unit_cents: int
    currency: str
    invoice_date: datetime.date
    due_date: datetime.date

    @property
    def total_cents(self):
        return self.qty * self.unit_cents


@dataclass(frozen=True)
class RowError:
    line: int
    code: str


@dataclass
class ImportResult:
    vendor: str
    records: list = field(default_factory=list)
    errors: list = field(default_factory=list)
