# t49-tiered-meter: where each hidden-test rule is shown

The repo has no docs folder. The prompt gives the tiers and prices, "after the lines of all the other
meters", and the line's `quantity` and `amount`. Everything else is shown by `meters/base.py`, the three
existing meters, `ops/invoices.py` and `service.py`. This file is outside `repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_the_meter_takes_usage` | a meter has a `name` (the value of `meter` in `usage.record`), is registered with `@meter`, imported in `meters/__init__.py`, and overrides `record()`; the total in the view comes from `get()` | `meters/registry.py`, `base.py` (`record` refuses by default, `name`); `units.py`, `allowance.py`; `service.meter`; `ops/invoices.py` `record` |
| `test_the_usage_event_carries_the_returned_view` | free once `record()` and `get()` are used | `ops/invoices.py` |
| `test_each_tier_has_its_price`, `test_usage_adds_up_across_calls` | tier arithmetic, in prices the prompt gives | prompt |
| `test_half_a_cent_rounds_up_once_per_line`, the amounts in `test_each_tier_has_its_price` (3, 7 and 1001 units) | prices are worked out in mills and turned into cents once, half up, by `Meter.cents()`; Python's `round()` and float prices give 22 and 52 for 3 and 7 units | `base.py` docstring and `cents`; `units.py`, `allowance.py` both go through `cents(...)` on the whole line |
| `test_no_usage_means_no_line` | nothing owed means no line | `base.py` (`settle` docstring); `units.py`, `allowance.py` return `[]` |
| `test_the_line_is_last_and_counts_in_the_total`, `test_the_line_names_its_invoice` | invoice lines come in meter priority order (lower first), so the meter needs a priority above 30; line shape comes from `Meter.line()` | `meters/registry.build`; `base.py` docstring; `flat.py` 10, `units.py` 20, `allowance.py` 30; prompt |
| `test_the_events_of_a_close_come_in_order` | free from `period.close` | `ops/invoices.py` |
| `TestPeriods` (all) | a customer's usage lives in `self.usage` (through `get()`), which `forget()` clears after every close; usage kept anywhere else carries over into the next period; the dict is per instance | `base.py` docstring, `__init__`, `get`, `forget`; `units.py`, `allowance.py`; `ops/invoices.py` `close` |
| `test_bad_quantities_change_nothing`, `test_customer_and_meter_are_checked_in_order`, `test_failed_calls_emit_nothing` | validation happens in the operation before `record()`; an override of `record()` that raises or checks on its own would break the order | `ops/invoices.py` `record`; `validate.require_qty` |
| `TestExisting` | regression | `tests/test_meterd.py` |

What makes it hard: three small conventions, each visible in two existing meters. Usage has to go
through `get()` and `self.usage` or the next period inherits it; the line has to come from `cents()`,
once, half up (a plain `round()` is wrong for 3 and 7 units); and the priority decides where the line
lands on the invoice. None is mentioned in the prompt beyond "build it the way the other meters are
built".
