`shopkit` prices a shopping cart: line items, a bulk discount, coupons, tax and shipping. Customers
report that some carts come out with the wrong total. Fix the library so that it meets this spec:

1. Money is whole cents (`int`). Rates are in basis points (1 bp = 0.01%, so 1000 bp = 10%). Every
   percentage of an amount, `amount * bp / 10000`, is rounded half up to a whole cent: a result
   that falls exactly halfway between two cents (for example 4.5) rounds up (to 5).
2. `Cart.add_item(sku, unit_price, qty=1)` needs an `int` `qty >= 1`, otherwise `ValueError`.
   Adding a sku that is already in the cart adds to that line's quantity instead of creating a
   second line; if the `unit_price` differs from the line's price, raise `ValueError`.
   `remove_item(sku)` removes the line (`KeyError` if the sku is not in the cart).
   `set_quantity(sku, qty)` replaces a line's quantity; `0` removes the line, a negative number
   raises `ValueError`, an unknown sku raises `KeyError`.
3. A line's price is `unit_price * qty`. Bulk discount: a line whose quantity is 10 or more gets
   10% off that line's price (percentage rule of R1, computed per line).
4. `Cart.apply_coupon(coupon)` adds a coupon. Coupons are applied in the order they were added,
   each one to the amount left after the bulk discounts and the coupons before it. A percent
   coupon takes its percentage off (R1); a fixed coupon takes its cents off. The amount never goes
   below 0: a fixed coupon larger than what is left brings it to 0.
5. Tax is `Cart(tax_bp=...)` basis points (default 0) of the amount left after bulk discounts and
   coupons, computed once on that whole amount. Shipping is not taxed.
6. Shipping is `SHIPPING_CENTS` (700), or 0 when the amount left after bulk discounts and coupons
   (before tax) is at least `FREE_SHIPPING_MIN_CENTS` (5000), or 0 for an empty cart. A cart that
   has items but whose amount is 0 still pays shipping.
7. `Cart.totals()` returns a dict with the keys `subtotal` (sum of line prices before any
   discount), `bulk_discount`, `coupon_discount`, `tax`, `shipping` and `total`, where
   `total = subtotal - bulk_discount - coupon_discount + tax + shipping`. It always reflects the
   cart's current items and coupons, including after later changes. An empty cart's values are
   all 0.

Keep the public names and signatures as they are. Use only the Python standard library.
Existing tests are in `tests/`.
