"""Report-wide constants."""
from decimal import Decimal

GAP = "  "  # between table columns
BASE_CURRENCY = "USD"
ZERO = Decimal("0.00")
TOTAL_LABEL = "TOTAL"
OTHER_LABEL = "Other"
MAX_LABEL_WIDTH = 20  # longer labels are shortened in the text table
ELLIPSIS = "..."
SKIPPED_SHOWN = 5  # issue lines listed under "Skipped N invalid rows"
