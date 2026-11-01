"""A small command line over a demo book: `python -m billkit.cli statement cus_0001`."""
import sys
from datetime import date

from .app import Billing
from .exports import invoices_csv, statement_text


def demo_book():
    app = Billing()
    app.catalog.add("starter", "Starter", "month", 2000, included_units=500)
    app.catalog.add("team", "Team", "month", 9000, included_units=5000)
    app.catalog.add("team-year", "Team (yearly)", "year", 90000, included_units=60000)
    cus = app.customers.create(name="Acme Ltd", email="billing@acme.test", region="uk")
    app.tax_rates.create(region="uk", label="VAT", bps=2000)
    app.subscribe(cus.id, "starter", date(2026, 4, 1), quantity=3)
    return app


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    app = demo_book()
    if not argv:
        print("usage: billkit.cli statement <customer> | invoices")
        return 2
    if argv[0] == "statement" and len(argv) == 2:
        print(statement_text(app, argv[1]), end="")
        return 0
    if argv[0] == "invoices":
        print(invoices_csv(app), end="")
        return 0
    print(f"unknown command {argv[0]!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
