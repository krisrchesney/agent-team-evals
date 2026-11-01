# t48-order-points: where each hidden-test rule is shown

The repo has no docs folder. The prompt gives the points rule, the cap, the event's fields,
`customer.points` and where the reaction sits ("after the limit checks ... before notifications").
Everything else is shown by `reactions/base.py`, the three existing reactions, `ops/orders.py` and
`service.py`. This file is outside `repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_operation_is_registered` | operation registered by name; the module must be imported | prompt; `ops/__init__.py` comment; `ops/registry.py` |
| `test_an_unknown_customer_has_nothing` | prompt rule (balance 0) | prompt |
| `test_one_point_per_full_ten`, `test_rounding_goes_down`, `test_the_event_carries_the_new_balance` | points arithmetic and event fields | prompt |
| `test_the_event_comes_between_the_order_and_the_notice`, `test_nothing_to_credit_means_no_event` | a reaction's events follow the move's own event, in priority order; the reaction must be registered with `@reaction`, imported in `reactions/__init__.py`, and have a `priority` between 20 and 90 (the default 50 does it); an `apply()` with nothing to say returns `[]` | `reactions/base.py` docstring; `registry.build`; `notify.py` ("Always last"), `daily_limit.py`, `daily_spend.py` |
| `test_only_delivery_awards_points`, `test_a_cancelled_order_earns_nothing`, `test_a_failed_delivery_...`, `test_delivering_twice_...` | `apply()` runs for every move, so the reaction has to look at `action`; failed moves run no reaction | `daily_limit.py` and `daily_spend.py` (`action == "pay"`); `ops/orders.py` `move` |
| `test_the_order_is_only_bumped_by_its_move` | awarding does not touch the order | `ops/orders.py` |
| `test_customer_is_read_like_other_strings` | `validate.require_str` and its `param` | every op in `ops/` |
| `TestDailyCap` (all) | per-day state lives in `self.state`, built by `fresh()` and replaced by `begin_day()`, which the service calls on the first call of each new day; the day is the clock's date at the time of the move | `reactions/base.py` docstring; `daily_limit.py`, `daily_spend.py` (`fresh`); `service._roll_day`; `tests/test_orderflow.py` day resets |
| `test_balances_are_not_a_daily_thing` | the balance is not daily state, so it must not live in `self.state` (the prompt calls it the customer's balance, and `customer.points` reads it on any day); it belongs in the store next to the orders | prompt; `store.py` |
| `test_the_cap_is_per_customer` | per-customer counters, like `DailySpend` | prompt; `daily_spend.py` |
| `test_the_limits_still_reset_each_day`, `test_pay_events_are_unchanged` | regression | `tests/test_orderflow.py` |

What makes it hard: the daily cap is state that has to be cleared by the base class's hook, while the
balance must not be. The obvious implementations either keep a plain dict on the instance (never
cleared, so the cap becomes lifetime), put the balance into `self.state` (wiped every day), or emit the
points event from the operation instead of a reaction (wrong place in the event order). The right
pattern is shown twice by the existing day-bound reactions.
