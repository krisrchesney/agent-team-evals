"""Hidden grader for t09. Test names start with the requirement (R1..R10) they check."""
import random
import unittest

from ledgerkit import InsufficientFunds, KeyConflict, Ledger


def make(**overdrafts):
    led = Ledger()
    for name in ("a", "b", "c"):
        led.open_account(name, overdraft=overdrafts.get(name, 0))
    return led


def snapshot(led):
    return ({n: led.balance(n) for n in "abc"}, {n: led.history(n) for n in "abc"})


class HiddenLedger(unittest.TestCase):
    # R1

    def test_r1_open_and_balance(self):
        led = Ledger()
        led.open_account("x")
        led.open_account("y", overdraft=50)
        self.assertEqual((led.balance("x"), led.balance("y")), (0, 0))

    def test_r1_duplicate_account(self):
        led = make()
        with self.assertRaises(ValueError):
            led.open_account("a")

    def test_r1_bad_overdraft(self):
        led = Ledger()
        for bad in (-1, 2.5, "5", True):
            with self.assertRaises(ValueError):
                led.open_account("x", overdraft=bad)
        with self.assertRaises(KeyError):
            led.balance("x")

    def test_r1_unknown_account_is_keyerror(self):
        led = make()
        led.deposit("a", 10)
        calls = [
            lambda: led.balance("zz"),
            lambda: led.deposit("zz", 1),
            lambda: led.withdraw("zz", 1),
            lambda: led.transfer("zz", "a", 1),
            lambda: led.transfer("a", "zz", 1),
            lambda: led.hold("zz", 1),
            lambda: led.available("zz"),
            lambda: led.history("zz"),
        ]
        for call in calls:
            with self.assertRaises(KeyError):
                call()

    # R2

    def test_r2_amount_must_be_positive_int(self):
        led = make(a=100)
        led.deposit("a", 10)
        before = snapshot(led)
        for bad in (0, -5, 1.5, True, "3", None):
            for call in (
                lambda: led.deposit("a", bad),
                lambda: led.withdraw("a", bad),
                lambda: led.transfer("a", "b", bad),
                lambda: led.hold("a", bad),
            ):
                with self.assertRaises(ValueError):
                    call()
        self.assertEqual(snapshot(led), before)
        self.assertEqual(led.deposit("b", 1), 2)  # no id was used up

    # R3

    def test_r3_available_formula(self):
        led = make(a=40)
        led.deposit("a", 100)
        self.assertEqual(led.available("a"), 140)
        led.hold("a", 30)
        self.assertEqual(led.available("a"), 110)
        self.assertEqual(led.balance("a"), 100)

    def test_r3_withdraw_to_exact_limit(self):
        led = make(a=100)
        led.deposit("a", 50)
        led.withdraw("a", 150)
        self.assertEqual(led.balance("a"), -100)
        self.assertEqual(led.available("a"), 0)
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 1)

    def test_r3_withdraw_one_over_limit(self):
        led = make(a=100)
        led.deposit("a", 50)
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 151)
        self.assertEqual(led.balance("a"), 50)
        self.assertEqual(led.history("a"), [(1, 50)])

    def test_r3_withdraw_respects_holds(self):
        led = make()
        led.deposit("a", 100)
        led.hold("a", 70)
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 31)
        led.withdraw("a", 30)
        self.assertEqual(led.available("a"), 0)

    # R4

    def test_r4_transfer_moves_money(self):
        led = make()
        led.deposit("a", 100)
        led.transfer("a", "b", 40)
        self.assertEqual((led.balance("a"), led.balance("b")), (60, 40))

    def test_r4_same_account(self):
        led = make()
        led.deposit("a", 100)
        with self.assertRaises(ValueError):
            led.transfer("a", "a", 10)
        self.assertEqual(led.history("a"), [(1, 100)])

    def test_r4_unknown_destination_changes_nothing(self):
        led = make()
        led.deposit("a", 100)
        with self.assertRaises(KeyError):
            led.transfer("a", "nobody", 10)
        self.assertEqual(led.balance("a"), 100)
        self.assertEqual(led.history("a"), [(1, 100)])
        self.assertEqual(led.deposit("b", 5), 2)

    def test_r4_insufficient_changes_nothing(self):
        led = make(a=10)
        led.deposit("a", 20)
        with self.assertRaises(InsufficientFunds):
            led.transfer("a", "b", 31)
        self.assertEqual(snapshot(led), ({"a": 20, "b": 0, "c": 0}, {"a": [(1, 20)], "b": [], "c": []}))

    def test_r4_transfer_to_exact_limit(self):
        led = make(a=10)
        led.transfer("a", "b", 10)
        self.assertEqual((led.balance("a"), led.balance("b")), (-10, 10))

    def test_r4_transfer_respects_holds(self):
        led = make()
        led.deposit("a", 100)
        led.hold("a", 60)
        with self.assertRaises(InsufficientFunds):
            led.transfer("a", "b", 41)
        led.transfer("a", "b", 40)
        self.assertEqual(led.balance("b"), 40)

    # R5

    def test_r5_ids_count_up_across_kinds(self):
        led = make()
        self.assertEqual(led.deposit("a", 100), 1)
        self.assertEqual(led.withdraw("a", 10), 2)
        self.assertEqual(led.transfer("a", "b", 10), 3)
        self.assertEqual(led.deposit("c", 1), 4)

    def test_r5_failures_use_no_id(self):
        led = make()
        led.deposit("a", 10)
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 11)
        with self.assertRaises(KeyError):
            led.transfer("a", "zz", 1)
        with self.assertRaises(ValueError):
            led.transfer("a", "a", 1)
        self.assertEqual(led.withdraw("a", 1), 2)

    def test_r5_capture_and_reverse_use_ids(self):
        led = make()
        led.deposit("a", 100)  # 1
        hid = led.hold("a", 10)
        self.assertEqual(led.capture(hid, "b"), 2)
        self.assertEqual(led.reverse(2), 3)
        self.assertEqual(led.deposit("a", 1), 4)

    # R6

    def test_r6_replay_does_not_move_money_twice(self):
        led = make()
        led.deposit("a", 100)
        first = led.transfer("a", "b", 30, key="k1")
        again = led.transfer("a", "b", 30, key="k1")
        self.assertEqual(first, again)
        self.assertEqual((led.balance("a"), led.balance("b")), (70, 30))
        self.assertEqual(led.deposit("c", 1), first + 1)

    def test_r6_key_conflict(self):
        led = make()
        led.deposit("a", 100)
        led.transfer("a", "b", 30, key="k1")
        for args in (("a", "b", 31), ("a", "c", 30), ("b", "a", 30)):
            with self.assertRaises(KeyConflict):
                led.transfer(*args, key="k1")
        self.assertTrue(issubclass(KeyConflict, ValueError))
        self.assertEqual((led.balance("a"), led.balance("b")), (70, 30))

    def test_r6_failed_attempt_keeps_key_free(self):
        led = make()
        with self.assertRaises(InsufficientFunds):
            led.transfer("a", "b", 30, key="k1")
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 30, key="k1")
        self.assertEqual(led.balance("b"), 30)
        self.assertEqual(led.transfer("a", "b", 30, key="k1"), txn)
        self.assertEqual(led.balance("b"), 30)

    def test_r6_failed_attempt_with_other_params_keeps_key_free(self):
        led = make()
        led.deposit("a", 10)
        with self.assertRaises(InsufficientFunds):
            led.transfer("a", "b", 50, key="k1")
        led.transfer("a", "c", 5, key="k1")
        self.assertEqual(led.balance("c"), 5)

    def test_r6_replay_even_if_funds_gone(self):
        led = make()
        led.deposit("a", 30)
        txn = led.transfer("a", "b", 30, key="k1")
        self.assertEqual(led.transfer("a", "b", 30, key="k1"), txn)
        self.assertEqual((led.balance("a"), led.balance("b")), (0, 30))

    def test_r6_replay_after_reversal(self):
        led = make()
        led.deposit("a", 30)
        txn = led.transfer("a", "b", 30, key="k1")
        led.reverse(txn)
        self.assertEqual(led.transfer("a", "b", 30, key="k1"), txn)
        self.assertEqual((led.balance("a"), led.balance("b")), (30, 0))

    def test_r6_keys_are_independent(self):
        led = make()
        led.deposit("a", 100)
        t1 = led.transfer("a", "b", 10, key="k1")
        t2 = led.transfer("a", "b", 10, key="k2")
        t3 = led.transfer("a", "b", 10)
        t4 = led.transfer("a", "b", 10)
        self.assertEqual(len({t1, t2, t3, t4}), 4)
        self.assertEqual(led.balance("b"), 40)

    # R7

    def test_r7_hold_lowers_available_only(self):
        led = make()
        led.deposit("a", 100)
        led.hold("a", 30)
        led.hold("a", 20)
        self.assertEqual((led.balance("a"), led.available("a")), (100, 50))

    def test_r7_hold_uses_overdraft(self):
        led = make(a=50)
        led.deposit("a", 10)
        led.hold("a", 60)
        with self.assertRaises(InsufficientFunds):
            led.hold("a", 1)

    def test_r7_hold_too_large(self):
        led = make()
        led.deposit("a", 100)
        led.hold("a", 60)
        with self.assertRaises(InsufficientFunds):
            led.hold("a", 41)
        self.assertEqual(led.available("a"), 40)

    def test_r7_hold_ids_separate_from_txn_ids(self):
        led = make()
        led.deposit("a", 100)
        led.deposit("a", 100)
        led.deposit("a", 100)
        self.assertEqual(led.hold("a", 1), 1)
        self.assertEqual(led.hold("a", 1), 2)
        self.assertEqual(led.deposit("a", 1), 4)

    def test_r7_failed_hold_uses_no_id(self):
        led = make()
        led.deposit("a", 10)
        with self.assertRaises(InsufficientFunds):
            led.hold("a", 11)
        self.assertEqual(led.hold("a", 10), 1)

    def test_r7_release_gives_funds_back(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 100)
        self.assertEqual(led.available("a"), 0)
        led.release(hid)
        self.assertEqual(led.available("a"), 100)
        led.withdraw("a", 100)

    def test_r7_release_unknown_or_twice(self):
        led = make()
        led.deposit("a", 100)
        with self.assertRaises(KeyError):
            led.release(99)
        hid = led.hold("a", 10)
        led.release(hid)
        with self.assertRaises(KeyError):
            led.release(hid)

    def test_r7_holds_are_per_account(self):
        led = make()
        led.deposit("a", 100)
        led.deposit("b", 100)
        led.hold("a", 100)
        self.assertEqual(led.available("b"), 100)

    # R8

    def test_r8_capture_withdraws_held_amount_once(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 100)
        txn = led.capture(hid)
        self.assertEqual(txn, 2)
        self.assertEqual((led.balance("a"), led.available("a")), (0, 0))
        self.assertEqual(led.history("a"), [(1, 100), (2, -100)])

    def test_r8_capture_keeps_other_holds(self):
        led = make()
        led.deposit("a", 100)
        h1 = led.hold("a", 30)
        led.hold("a", 20)
        led.capture(h1)
        self.assertEqual((led.balance("a"), led.available("a")), (70, 50))

    def test_r8_capture_to_destination(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 40)
        txn = led.capture(hid, dst="b")
        self.assertEqual((led.balance("a"), led.balance("b")), (60, 40))
        self.assertEqual(led.history("b"), [(txn, 40)])
        self.assertEqual(led.available("a"), 60)

    def test_r8_capture_never_fails_for_funds(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 100)
        with self.assertRaises(InsufficientFunds):
            led.withdraw("a", 1)
        led.capture(hid, dst="b")
        self.assertEqual(led.balance("b"), 100)

    def test_r8_capture_twice_or_unknown(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 10)
        led.capture(hid)
        with self.assertRaises(KeyError):
            led.capture(hid)
        with self.assertRaises(KeyError):
            led.capture(42)
        with self.assertRaises(KeyError):
            led.release(hid)

    def test_r8_capture_after_release_fails(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 10)
        led.release(hid)
        with self.assertRaises(KeyError):
            led.capture(hid)

    def test_r8_capture_unknown_destination_keeps_hold(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 40)
        with self.assertRaises(KeyError):
            led.capture(hid, dst="nobody")
        self.assertEqual(led.available("a"), 60)
        self.assertEqual(led.balance("a"), 100)
        self.assertEqual(led.capture(hid, dst="b"), 2)

    def test_r8_capture_to_holder_keeps_hold(self):
        led = make()
        led.deposit("a", 100)
        hid = led.hold("a", 40)
        with self.assertRaises(ValueError):
            led.capture(hid, dst="a")
        self.assertEqual(led.available("a"), 60)
        led.release(hid)
        self.assertEqual(led.available("a"), 100)

    # R9

    def test_r9_reverse_transfer(self):
        led = make()
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 40)
        rev = led.reverse(txn)
        self.assertEqual(rev, 3)
        self.assertEqual((led.balance("a"), led.balance("b")), (100, 0))
        self.assertEqual(led.history("a"), [(1, 100), (2, -40), (3, 40)])
        self.assertEqual(led.history("b"), [(2, 40), (3, -40)])

    def test_r9_reverse_capture_to_destination(self):
        led = make()
        led.deposit("a", 100)
        txn = led.capture(led.hold("a", 40), dst="b")
        led.reverse(txn)
        self.assertEqual((led.balance("a"), led.balance("b")), (100, 0))

    def test_r9_reverse_only_once(self):
        led = make()
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 40)
        led.reverse(txn)
        before = snapshot(led)
        with self.assertRaises(ValueError):
            led.reverse(txn)
        self.assertEqual(snapshot(led), before)

    def test_r9_reversal_cannot_be_reversed(self):
        led = make()
        led.deposit("a", 100)
        rev = led.reverse(led.transfer("a", "b", 40))
        with self.assertRaises(ValueError):
            led.reverse(rev)

    def test_r9_deposit_and_withdraw_not_reversible(self):
        led = make()
        d = led.deposit("a", 100)
        w = led.withdraw("a", 10)
        c = led.capture(led.hold("a", 10))
        for txn in (d, w, c):
            with self.assertRaises(ValueError):
                led.reverse(txn)

    def test_r9_unknown_txn(self):
        led = make()
        with self.assertRaises(KeyError):
            led.reverse(7)

    def test_r9_insufficient_leaves_transfer_reversible(self):
        led = make()
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 40)
        led.withdraw("b", 30)
        before = snapshot(led)
        with self.assertRaises(InsufficientFunds):
            led.reverse(txn)
        self.assertEqual(snapshot(led), before)
        led.deposit("b", 30)
        led.reverse(txn)
        self.assertEqual((led.balance("a"), led.balance("b")), (100, 0))

    def test_r9_reverse_respects_holds_on_destination(self):
        led = make()
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 40)
        hid = led.hold("b", 1)
        with self.assertRaises(InsufficientFunds):
            led.reverse(txn)
        led.release(hid)
        led.reverse(txn)

    def test_r9_reverse_allowed_down_to_overdraft_limit(self):
        led = make(b=10)
        led.deposit("a", 100)
        txn = led.transfer("a", "b", 40)
        led.withdraw("b", 50)  # b = -10, exactly at its limit
        self.assertEqual(led.available("b"), 0)
        with self.assertRaises(InsufficientFunds):
            led.reverse(txn)
        led.deposit("b", 40)
        led.reverse(txn)
        self.assertEqual(led.balance("b"), -10)

    # R10

    def test_r10_history_entries(self):
        led = make()
        led.deposit("a", 100)
        led.withdraw("a", 10)
        led.transfer("a", "b", 20)
        self.assertEqual(led.history("a"), [(1, 100), (2, -10), (3, -20)])
        self.assertEqual(led.history("b"), [(3, 20)])
        self.assertEqual(led.history("c"), [])

    def test_r10_history_is_a_copy(self):
        led = make()
        led.deposit("a", 100)
        led.history("a").append((99, 99))
        self.assertEqual(led.history("a"), [(1, 100)])

    def test_r10_total(self):
        led = make()
        self.assertEqual(led.total(), 0)
        led.deposit("a", 100)
        led.deposit("b", 50)
        led.transfer("a", "c", 70)
        self.assertEqual(led.total(), 150)
        led.withdraw("c", 20)
        self.assertEqual(led.total(), 130)

    def test_r10_random_operations_keep_invariants(self):
        rng = random.Random(9)
        led = Ledger()
        names = ["a", "b", "c", "d"]
        for n in names:
            led.open_account(n, overdraft=rng.choice([0, 0, 25, 100]))
        external = 0  # deposits minus withdrawals and plain captures
        holds = {}  # hold id -> (account, amount)
        transfers = []
        last_id = 0
        for _ in range(600):
            op = rng.choice(["dep", "wd", "tr", "tr", "hold", "rel", "cap", "rev"])
            n = rng.choice(names)
            m = rng.choice([x for x in names if x != n])
            amt = rng.randint(1, 80)
            txn = None
            try:
                if op == "dep":
                    txn = led.deposit(n, amt)
                    external += amt
                elif op == "wd":
                    txn = led.withdraw(n, amt)
                    external -= amt
                elif op == "tr":
                    txn = led.transfer(n, m, amt, key=rng.choice([None, "k%d" % rng.randint(0, 15)]))
                    if txn == last_id + 1:
                        transfers.append(txn)
                elif op == "hold":
                    holds[led.hold(n, amt)] = (n, amt)
                elif op == "rel" and holds:
                    h = rng.choice(sorted(holds))
                    led.release(h)
                    del holds[h]
                elif op == "cap" and holds:
                    h = rng.choice(sorted(holds))
                    holder, held_amt = holds[h]
                    if rng.random() < 0.5:
                        txn = led.capture(h)
                        external -= held_amt
                    else:
                        txn = led.capture(h, dst=next(x for x in names if x != holder))
                        transfers.append(txn)
                    del holds[h]
                elif op == "rev" and transfers:
                    txn = led.reverse(rng.choice(transfers))
            except (InsufficientFunds, ValueError):
                pass
            if txn is not None:
                if txn != last_id + 1:  # only an idempotent replay may return an old id
                    self.assertLessEqual(txn, last_id)
                    self.assertIn(txn, transfers)
                else:
                    last_id = txn
            for x in names:
                self.assertGreaterEqual(led.available(x), 0)
                self.assertEqual(sum(d for _, d in led.history(x)), led.balance(x))
        self.assertEqual(led.total(), external)
        ids = {i for x in names for i, _ in led.history(x)}
        self.assertEqual(ids, set(range(1, last_id + 1)))

if __name__ == "__main__":
    unittest.main()
