`books` keeps every amount as integer cents in one implicit currency, USD. We now invoice and bank in
other currencies, so make the whole library multi-currency. Everything that works today in USD must
keep working exactly as it does (tests are in `tests/`). Use only the Python standard library.

1. **Currencies.** `books.money.EXPONENTS` gives the decimals of each supported currency: USD, EUR and
   GBP 2, JPY 0, KWD 3. An amount is an integer in the minor unit of its currency (1500 JPY is 1500;
   1500 KWD is 1.500). An unknown currency raises `UnknownCurrency` (code `unknown_currency`,
   `param="currency"`). `parse_amount(text, currency="USD")`, `format_amount(minor, currency="USD")` and
   `to_decimal_string(minor, currency="USD")` take the currency; text with more decimals than the
   currency has is `InvalidAmount`, and a plain int is a number of whole units. `format_amount` keeps
   `$1,234.50` for USD and writes other currencies as `1,234.50 EUR` and `1,500 JPY`.
2. **Accounts.** `create_account(code, name, kind, currency="USD")`. An account has a `currency`
   (also in the dict `create_account` returns) and its balances are in that currency.
3. **Postings.** An entry may mix currencies, but it must add up to zero in each currency separately,
   otherwise `Unbalanced`. A posting is in its account's currency. A line may also carry
   `"currency"`; if it differs from the account's, raise `CurrencyMismatch` (code `currency_mismatch`,
   `param="currency"`). Line amounts are text in the account's currency. Every posting an entry
   returns (also from `Ledger.post` and `Ledger.void`) has a `currency`.
4. **Rates.** `Ledger.rates` holds exchange rates. `rates.set(base, quote, rate, on)` records that one
   major unit of `base` is `rate` major units of `quote` from the date `on` (`InvalidRate` if the rate
   is not a positive number or base equals quote). `rates.get(base, quote, on=None)` returns a
   `Decimal`: the latest rate dated on or before `on` (the latest of all when `on` is None); if there
   is no direct rate it is 1 divided by the reverse pair's rate; a direct rate always wins; the same
   currency gives 1; otherwise `NoRate` (code `no_rate`, `param="currency"`).
   `rates.convert(minor, base, quote, on=None)` converts an amount in minor units, allowing for the
   two currencies' decimals, rounded half away from zero.
5. **Trial balance.** Rows get a `currency`. `totals` maps each currency to `{"debit", "credit"}`.
   `total_debit` and `total_credit` stay and hold the USD totals (0 if there are none). `balanced` is
   true when every currency balances.
6. **Statements.** `balance_sheet(as_of=None, currency="USD")` and
   `income_statement(start, end, currency="USD")` report in that currency. Convert each account's
   balance on its own (not a sum of several), at the rate on `as_of` for the balance sheet and on `end`
   for the income statement. Both results carry `currency`. The balance sheet's `balanced` is judged in
   each account's own currency, before converting. `statement(code, ...)` stays in the account's
   currency, carries `currency`, and its `display` strings use that currency's format.
7. **Budgets.** `budgets.set(account, month, limit, currency=None)`: the budget's currency defaults to
   the account's, `limit` is in it, and `status` carries `currency`. Spending is in the budget's
   currency: convert each posting at the rate on that posting's own date.
8. **Invoices.** An invoice is in the currency of its `receivable` account; unit prices, tax and
   totals are in it and the invoice dict has `currency`. The revenue, tax and bank accounts must be in
   that currency too (`CurrencyMismatch`, and nothing is recorded). `invoices.aging(as_of,
   currency="USD")` converts each invoice's outstanding amount on its own, at the rate on `as_of`,
   and carries `currency`.
9. **Recurring entries.** A template must add up to zero in each currency when it is added.
10. **Interest.** `interest.accrue` works in the account's currency; the income account must be in the
    same currency (`CurrencyMismatch`); the result carries `currency` and a `display` in that currency.
11. **Reconciliation.** Statement amounts and `tolerance` are in the account's currency. The result
    carries `currency` and its `display` strings use it.
12. **CSV.** `export_entries` adds a `currency` column after `amount` and writes each amount with its
    currency's decimals. `import_entries` accepts files with or without that column (without it, each
    amount is in its account's currency); a currency that differs from the account's is
    `CurrencyMismatch`.
13. **Save and load.** `Ledger.dump()` records account and posting currencies and the rates, and still
    survives `json.dumps`. `Ledger.load()` restores all of it and still reads older dumps that have
    no currencies (everything USD, no rates).
14. **Summary.** `Ledger.summary(as_of=None, currency="USD")` converts each account's balance on its
    own at the rate on `as_of`, and carries `currency`. As in the reports, an account whose balance
    is zero is skipped, so it never needs a rate.
