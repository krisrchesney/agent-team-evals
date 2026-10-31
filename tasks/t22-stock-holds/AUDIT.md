# t22-stock-holds: where each hidden-test rule is shown

The repo has no docs folder: every rule the hidden tests check, beyond the prompt, is shown by the
existing code, usually by every existing operation doing it the same way. This file is outside `repo/`,
so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_operations_are_registered` | new operations registered by name; the module must be imported | prompt (names); `ops/__init__.py` comment "importing a module registers its operations"; `ops/registry.py` |
| `test_hold_view` | id from `svc.ids.new(<noun>)`; `created_at`/`updated_at`/`version 1`; timestamps via `stamp()`; `expires_at` = created + 15 min | `ops/items.py` (`Item` ids, created=updated=now, version default 1); `views.py` `stamp`; prompt (15 minutes) |
| `test_ids_are_sequential` | ids come from `Ids`, prefix = noun | `ids.py`; `item_...`, `mv_...` in `ops/` |
| `test_order_is_stripped_like_other_strings` | strings read with `validate.require_str` | every op in `ops/` |
| `test_available_drops_on_hand_does_not`, `_in_list_too` | `available` in the item view is the shippable amount; holds lower it, `on_hand` is physical stock | `views.available` used by `stock.ship`; prompt ("nobody else can get that stock") |
| `test_cannot_hold_more_than_available` | `InsufficientStock` with `param="quantity"` | `ops/stock.py` `ship` |
| `test_create_event`, `test_release` event, `test_capture_event` | one event per mutation, named `<noun>.<past tense>`, data `{"<noun>": view}` equal to the return value | `item.created`, `stock.received` etc. in `ops/` |
| `test_create_records_no_movement`, release has no movement | a movement is a change to `on_hand` only | `models.Movement` docstring "Nothing else is a movement" |
| `test_unknown_item`, `test_item_checked_before_quantity` | `store.get_item` first (NotFound, `param="item"`), then validation | order of checks in every `ops/stock.py` op |
| `test_bad_quantities`, `test_missing_order` | `validate.require_qty`, `validate.require_str` and their params | `ops/stock.py` `ship` (same arguments, per the prompt) |
| `test_failures_change_nothing` | validate before any change; ids are only taken after validation; no event on failure | every op in `ops/` |
| `test_unknown_hold`, `test_missing_hold_id` | a getter like `get_item` raising NotFound with `param` = argument name; id read with `require_str` | `store.get_item`; `item.retrieve` |
| `test_ship_cannot_take_held_stock` | `stock.ship` compares with `available`, so held stock is not shippable | `ops/stock.py` `ship`; prompt |
| `test_release`, `test_capture` versions and times | every change goes through `store.bump(record, now)` (version + 1, `updated_at`) | every mutating op |
| `test_capture` item fields | capturing changes `on_hand`, so the item is bumped too | `ops/stock.py` `ship` |
| `test_capture_is_a_shipment_movement` | capture is a shipment: `ship` movement, `-quantity`, `ref` = order | prompt ("turns the hold into a shipment"); `ops/stock.py` `ship` |
| `test_*_conflicts` | acting on a hold that is not active is a `Conflict` | `errors.Conflict`; `item.create` duplicate sku |
| `TestExpiry` | a hold stops counting 15 minutes after it was made, in every read and write | prompt (lasts 15 minutes, `expired` status); `available` feeds every item view |
| `test_retrieve` | reads emit no events | `item.retrieve`, `stock.movements` |
| `test_existing_operations_unchanged` | regression | `tests/test_stock.py`, `ops/` |

What makes it hard: nothing says how to name ids, events or errors, that holds are not movements, that
capture must be a movement and bump the item, or that expiry has to show up in reads like
`item.retrieve` and `item.list` (which do not read the clock today). All of it is visible in how the
existing operations are written.
