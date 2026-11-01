"""books: a small double-entry ledger.

    from books.ledger import Ledger
    led = Ledger()
    led.create_account("1000", "Cash", "asset")
    led.create_account("4000", "Sales", "income")
    led.post("2026-01-05", "first sale", [{"account": "1000", "amount": "25.00"},
                                          {"account": "4000", "amount": "-25.00"}])
"""
