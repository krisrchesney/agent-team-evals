`shop` prices an order against a catalog (`price_order(order, catalog) -> Quote`), prints an invoice
(`invoice.render_invoice`), can read JSON files (`loader.py`) and has a small CLI
(`python -m shop CATALOG.json ORDER.json [--json]`). All money is integer cents. Add bundle deals and
coupons, and carry them through the whole pipeline:

1. `Item` gets a last field `bundle=None`. A bundle is a pair `(n, m)` of ints with `n > m >= 1`
   meaning "pay for `m` of every `n` units". Constructing an `Item` with any other non-`None`
   bundle (wrong length, non-int, `m < 1`, `n <= m`) raises `ValueError`.
2. For a line of `qty` units of an item with bundle `(n, m)`, the units charged are
   `(qty // n) * m + qty % n`, and the line's `bundle_discount_cents` is
   `(qty - charged) * unit price`. A line without a bundle has `bundle_discount_cents == 0`.
3. `Order` becomes `Order(lines, customer="", coupons=())`; `coupons` is a sequence of coupon-code
   strings. `LineQuote` gets two more int fields with default 0, `bundle_discount_cents` and
   `coupon_discount_cents`, plus read-only properties `discount_cents` (their sum) and `net_cents`
   (`gross_cents - discount_cents`). `Quote` gets `discount_cents` (the sum over its lines) and
   `coupons` (a tuple of `shop.coupons.AppliedCoupon(code, amount_cents)`, see 6). `subtotal_cents`
   stays the sum of the gross line amounts, and `total_cents = subtotal_cents - discount_cents + tax_cents`.
4. A line's tax is computed on its `net_cents` (after bundle and coupon discounts), with the same
   rates and the same half-up rounding as today. Non-taxable lines stay at 0.
5. Coupons live in a new module `shop/coupons.py`, which also defines `UnknownCoupon` (a subclass
   of `ValueError`) and `AppliedCoupon`. A code is matched after stripping whitespace and upper-casing
   it. If the same code appears more than once, only its first occurrence counts. `price_order` raises
   `UnknownCoupon` for a code that is not in this table:
   - `SAVE10`: 10% off every line.
   - `FOOD20`: 20% off the lines whose item category is `"food"`.
   - `FIVEOFF`: 500 cents off every line, but only if the total net of all lines, at that
     point, is at least 5000.
6. Coupons are applied in the order given. Each one sees the line nets left after the bundle
   discounts and after the coupons before it. A percentage coupon's amount is
   `eligible net * percent / 100` rounded half up to a whole cent; `FIVEOFF`'s amount is
   `min(500, eligible net)`. "Eligible" lines are the lines the coupon covers whose net is above 0.
   A coupon whose condition is not met, or whose amount is 0, is skipped: it is not in
   `Quote.coupons` and it is not an error. Otherwise it is recorded as
   `AppliedCoupon(code_in_upper_case, full_amount)`, in the order applied.
7. A coupon's amount is split over its eligible lines in proportion to their current net. Each line
   first gets `floor(amount * line_net / eligible_net)` cents; the cents still left over go one each
   to the lines with the largest remainders of `amount * line_net % eligible_net`, ties to the earlier
   line. A line's `coupon_discount_cents` is the sum of its shares from all coupons.
8. `render_invoice` is unchanged for a quote with `discount_cents == 0`. Otherwise it inserts, right
   after the `Subtotal:` line and before `Tax:`: one line `  Bundle <name>: -X.XX` for each line with a
   bundle discount, in line order; one line `  Coupon <CODE>: -X.XX` for each applied coupon, in the
   order applied; then `Discount: -X.XX` with the total discount. (`X.XX` is formatted as the
   other amounts are.)
9. `loader.catalog_from_list` accepts an optional `"bundle": [n, m]` in an item row.
   `loader.order_from_dict` accepts an optional `"coupons"` list (default: none).
   `loader.quote_to_dict` keeps every key it has today with the same meaning and adds: in each
   line `bundle_discount_cents`, `coupon_discount_cents` and `net_cents`; at the top level
   `discount_cents` and `coupons` (a list of `{"code": ..., "amount_cents": ...}`). The new keys
   are always present, also when they are zero or empty.
10. The CLI gets a repeatable option `--coupon CODE`. Its codes are added after the coupons in the
    order file. If a code is unknown, `main()` prints `shop: error: unknown coupon 'CODE'` to stderr
    (`CODE` stripped and upper-cased), prints nothing to stdout and returns 2. On success it
    still returns 0.
11. Orders without bundles or coupons must price, print and serialise exactly as they do today.

Standard library only. Existing tests are in `tests/`.
