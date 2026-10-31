import unittest

from stockroom import Service
from stockroom.clock import FixedClock
from stockroom.errors import InsufficientStock, InvalidRequest, NotFound


class StockTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.item = self.svc.call("item.create", sku="mug-01", name="Mug")

    def test_create_item(self):
        self.assertEqual(self.item["id"], "item_0001")
        self.assertEqual(self.item["sku"], "MUG-01")
        self.assertEqual(self.item["on_hand"], 0)
        self.assertEqual(self.item["created_at"], "2026-01-05T09:00:00Z")

    def test_receive_and_ship(self):
        self.svc.call("stock.receive", item=self.item["id"], quantity=5)
        self.clock.advance(minutes=1)
        out = self.svc.call("stock.ship", item=self.item["id"], quantity=2, order="ord-1")
        self.assertEqual((out["on_hand"], out["available"], out["version"]), (3, 3, 3))
        self.assertEqual(out["updated_at"], "2026-01-05T09:01:00Z")
        kinds = [m["kind"] for m in self.svc.call("stock.movements", item=self.item["id"])["data"]]
        self.assertEqual(kinds, ["receive", "ship"])

    def test_cannot_ship_more_than_available(self):
        self.svc.call("stock.receive", item=self.item["id"], quantity=1)
        with self.assertRaises(InsufficientStock):
            self.svc.call("stock.ship", item=self.item["id"], quantity=2, order="ord-1")

    def test_errors(self):
        with self.assertRaises(NotFound):
            self.svc.call("stock.receive", item="item_9999", quantity=1)
        with self.assertRaises(InvalidRequest):
            self.svc.call("stock.receive", item=self.item["id"], quantity=0)

    def test_events(self):
        self.svc.call("stock.receive", item=self.item["id"], quantity=3)
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["item.created", "stock.received"])


if __name__ == "__main__":
    unittest.main()
