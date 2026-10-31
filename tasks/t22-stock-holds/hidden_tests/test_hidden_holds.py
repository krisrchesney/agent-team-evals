"""Hidden tests for t22-stock-holds. Every rule is shown by the starting code; see AUDIT.md."""
import unittest

from stockroom import Service
from stockroom.clock import FixedClock
from stockroom.errors import Conflict, InsufficientStock, InvalidRequest, NotFound, StockError

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.mug = self.svc.call("item.create", sku="mug-01", name="Mug")["id"]
        self.cap = self.svc.call("item.create", sku="cap-01", name="Cap")["id"]
        self.svc.call("stock.receive", item=self.mug, quantity=10)
        self.svc.call("stock.receive", item=self.cap, quantity=4)
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def hold(self, quantity=3, item=None, order="ord-1"):
        return self.call("hold.create", item=item or self.mug, quantity=quantity, order=order)

    def item(self, item_id=None):
        return self.call("item.retrieve", item=item_id or self.mug)

    def movements(self, item_id=None):
        return self.call("stock.movements", item=item_id or self.mug)["data"]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, StockError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestRegistration(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"hold.create", "hold.release", "hold.capture", "hold.retrieve"} <= ops)
        self.assertTrue({"item.create", "stock.ship", "stock.movements"} <= ops)


class TestCreate(Base):
    def test_hold_view(self):
        h = self.hold()
        self.assertEqual(h["id"], "hold_0001")
        self.assertEqual((h["item"], h["order"], h["quantity"], h["status"]), (self.mug, "ord-1", 3, "active"))
        self.assertEqual((h["created_at"], h["updated_at"], h["version"]), (T0, T0, 1))
        self.assertEqual(h["expires_at"], "2026-01-05T09:15:00Z")

    def test_ids_are_sequential(self):
        self.assertEqual([self.hold(1)["id"], self.hold(1)["id"]], ["hold_0001", "hold_0002"])

    def test_order_is_stripped_like_other_strings(self):
        self.assertEqual(self.hold(order="  ord-9 ")["order"], "ord-9")

    def test_available_drops_on_hand_does_not(self):
        self.hold(3)
        it = self.item()
        self.assertEqual((it["on_hand"], it["available"]), (10, 7))
        self.assertEqual(self.item(self.cap)["available"], 4)

    def test_available_in_list_too(self):
        self.hold(3)
        listed = {i["id"]: i for i in self.call("item.list")["data"]}
        self.assertEqual(listed[self.mug]["available"], 7)

    def test_cannot_hold_more_than_available(self):
        self.hold(8)
        self.assertError(InsufficientStock, "quantity", "hold.create", item=self.mug, quantity=3, order="o2")
        self.hold(2, order="o3")

    def test_create_event(self):
        h = self.hold()
        self.assertEqual(self.svc.bus.log, [{"type": "hold.created", "data": {"hold": h}}])

    def test_create_records_no_movement(self):
        self.hold()
        self.assertEqual([m["kind"] for m in self.movements()], ["receive"])


class TestValidation(Base):
    def test_unknown_item(self):
        self.assertError(NotFound, "item", "hold.create", item="item_9999", quantity=1, order="o")

    def test_item_checked_before_quantity(self):
        self.assertError(NotFound, "item", "hold.create", item="item_9999", quantity=0, order="o")

    def test_bad_quantities(self):
        for q in (0, -1, True, "3", 10_001, 2.0):
            with self.subTest(q=q):
                self.assertError(InvalidRequest, "quantity", "hold.create", item=self.mug, quantity=q, order="o")

    def test_missing_order(self):
        self.assertError(InvalidRequest, "order", "hold.create", item=self.mug, quantity=1)
        self.assertError(InvalidRequest, "order", "hold.create", item=self.mug, quantity=1, order="  ")

    def test_failures_change_nothing(self):
        for params in ({"item": "item_9999", "quantity": 1, "order": "o"},
                       {"item": self.mug, "quantity": 0, "order": "o"},
                       {"item": self.mug, "quantity": 11, "order": "o"}):
            with self.assertRaises(StockError):
                self.call("hold.create", **params)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.item()["available"], 10)
        self.assertEqual(self.hold(1)["id"], "hold_0001")

    def test_unknown_hold(self):
        for op in ("hold.release", "hold.capture", "hold.retrieve"):
            with self.subTest(op=op):
                self.assertError(NotFound, "hold", op, hold="hold_9999")

    def test_missing_hold_id(self):
        self.assertError(InvalidRequest, "hold", "hold.release")


class TestShipRespectsHolds(Base):
    def test_ship_cannot_take_held_stock(self):
        self.hold(8)
        self.assertError(InsufficientStock, "quantity", "stock.ship", item=self.mug, quantity=3, order="o2")
        out = self.call("stock.ship", item=self.mug, quantity=2, order="o2")
        self.assertEqual((out["on_hand"], out["available"]), (8, 0))


class TestRelease(Base):
    def test_release(self):
        h = self.hold(3)
        self.clock.advance(minutes=2)
        self.svc.bus.log.clear()
        r = self.call("hold.release", hold=h["id"])
        self.assertEqual((r["status"], r["version"], r["updated_at"]), ("released", 2, "2026-01-05T09:02:00Z"))
        self.assertEqual(r["created_at"], T0)
        self.assertEqual(self.item()["available"], 10)
        self.assertEqual(self.svc.bus.log, [{"type": "hold.released", "data": {"hold": r}}])
        self.assertEqual([m["kind"] for m in self.movements()], ["receive"])

    def test_release_twice_conflicts(self):
        h = self.hold()
        self.call("hold.release", hold=h["id"])
        self.svc.bus.log.clear()
        self.assertError(Conflict, "hold", "hold.release", hold=h["id"])
        self.assertEqual(self.svc.bus.log, [])

    def test_capture_after_release_conflicts(self):
        h = self.hold()
        self.call("hold.release", hold=h["id"])
        self.assertError(Conflict, "hold", "hold.capture", hold=h["id"])
        self.assertEqual(self.item()["on_hand"], 10)


class TestCapture(Base):
    def test_capture(self):
        h = self.hold(3, order="ord-7")
        self.clock.advance(minutes=5)
        c = self.call("hold.capture", hold=h["id"])
        self.assertEqual((c["status"], c["version"], c["updated_at"]), ("captured", 2, "2026-01-05T09:05:00Z"))
        it = self.item()
        self.assertEqual((it["on_hand"], it["available"]), (7, 7))
        self.assertEqual(it["updated_at"], "2026-01-05T09:05:00Z")

    def test_capture_is_a_shipment_movement(self):
        h = self.hold(3, order="ord-7")
        self.call("hold.capture", hold=h["id"])
        mvs = self.movements()
        self.assertEqual([(m["kind"], m["delta"], m["ref"]) for m in mvs], [("receive", 10, "delivery"),
                                                                           ("ship", -3, "ord-7")])
        self.assertEqual(mvs[-1]["id"], "mv_0003")

    def test_capture_event(self):
        h = self.hold()
        self.svc.bus.log.clear()
        c = self.call("hold.capture", hold=h["id"])
        types = [e["type"] for e in self.svc.bus.log]
        self.assertEqual(types[0], "hold.captured")
        self.assertEqual(self.svc.bus.log[0]["data"]["hold"], c)

    def test_capture_twice_conflicts_and_changes_nothing(self):
        h = self.hold(3)
        self.call("hold.capture", hold=h["id"])
        self.svc.bus.log.clear()
        self.assertError(Conflict, "hold", "hold.capture", hold=h["id"])
        self.assertEqual(self.item()["on_hand"], 7)
        self.assertEqual(len(self.movements()), 2)
        self.assertEqual(self.svc.bus.log, [])

    def test_release_after_capture_conflicts(self):
        h = self.hold()
        self.call("hold.capture", hold=h["id"])
        self.assertError(Conflict, "hold", "hold.release", hold=h["id"])


class TestExpiry(Base):
    def test_still_active_before_15_minutes(self):
        h = self.hold(3)
        self.clock.advance(minutes=14, seconds=59)
        self.assertEqual(self.call("hold.retrieve", hold=h["id"])["status"], "active")
        self.assertEqual(self.item()["available"], 7)
        self.assertEqual(self.call("hold.capture", hold=h["id"])["status"], "captured")

    def test_expired_after_15_minutes(self):
        h = self.hold(3)
        self.clock.advance(minutes=15, seconds=1)
        self.assertEqual(self.call("hold.retrieve", hold=h["id"])["status"], "expired")
        self.assertEqual(self.item()["available"], 10)

    def test_expired_stock_can_be_shipped_and_held_again(self):
        self.hold(10)
        self.clock.advance(minutes=16)
        self.assertEqual(self.hold(10, order="o2")["status"], "active")
        self.call("hold.release", hold="hold_0002")
        self.assertEqual(self.call("stock.ship", item=self.mug, quantity=10, order="o3")["on_hand"], 0)

    def test_expired_hold_cannot_be_captured_or_released(self):
        h = self.hold(3)
        self.clock.advance(minutes=20)
        self.svc.bus.log.clear()
        self.assertError(Conflict, "hold", "hold.capture", hold=h["id"])
        self.assertError(Conflict, "hold", "hold.release", hold=h["id"])
        self.assertEqual(self.item()["on_hand"], 10)
        self.assertNotIn("hold.captured", [e["type"] for e in self.svc.bus.log])


class TestRetrieve(Base):
    def test_retrieve(self):
        h = self.hold()
        self.svc.bus.log.clear()
        self.assertEqual(self.call("hold.retrieve", hold=h["id"]), h)
        self.assertEqual(self.svc.bus.log, [])


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        out = self.call("stock.adjust", item=self.cap, delta=-1, reason="broken")
        self.assertEqual((out["on_hand"], out["available"], out["version"]), (3, 3, 3))
        self.assertEqual(self.item()["available"], 10)
        with self.assertRaises(InsufficientStock):
            self.call("stock.ship", item=self.cap, quantity=4, order="o")


if __name__ == "__main__":
    unittest.main()
