import unittest

from ledgerkit import InsufficientFunds, Ledger


class TestLedger(unittest.TestCase):
    def test_deposit_and_withdraw(self):
        led = Ledger()
        led.open_account("a")
        led.deposit("a", 100)
        led.withdraw("a", 30)
        self.assertEqual(led.balance("a"), 70)

    def test_withdraw_too_much(self):
        led = Ledger()
        led.open_account("a")
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 1)

    def test_transfer(self):
        led = Ledger()
        led.open_account("a")
        led.open_account("b")
        led.deposit("a", 50)
        led.transfer("a", "b", 20)
        self.assertEqual((led.balance("a"), led.balance("b")), (30, 20))


if __name__ == "__main__":
    unittest.main()
