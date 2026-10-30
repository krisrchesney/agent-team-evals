`ledgerkit.Ledger` is a small in-memory money ledger. It only does the basics today. Extend and fix it
so that it meets the spec below. Amounts are integer cents.

**Accounts and amounts**

R1. `open_account(name, overdraft=0)` creates an account with balance 0. `overdraft` is a non-negative
    int: how far below zero the balance may go. A duplicate name, or a negative or non-int overdraft,
    raises `ValueError`. `balance(name)` returns the balance. Any method that is given an account name
    that does not exist raises `KeyError`.
R2. Every amount (deposit, withdraw, transfer, hold) must be an `int` greater than zero. Anything else
    (zero, negative, float, `bool`, string) raises `ValueError`, and nothing changes.

**Money movement**

R3. `available(name)` is `balance + overdraft - held`, where `held` is the total of that account's
    active holds (see R7). `withdraw(name, amount)` raises `InsufficientFunds` if `amount` is more than
    `available(name)`. Taking available to exactly 0 is allowed. A failed call changes nothing.
R4. `transfer(src, dst, amount, key=None)` moves `amount` from `src` to `dst` and is all-or-nothing:
    if it raises, no balance, history entry or id has changed. It raises `ValueError` if `src == dst`,
    `KeyError` for an unknown account, and `InsufficientFunds` if `amount` is more than
    `available(src)`.
R5. Every successful `deposit`, `withdraw`, `transfer`, `capture` (R8) and `reverse` (R9) posts one
    transaction and returns its id. Ids are ints counting up from 1 in the order transactions are
    posted. Calls that raise do not use up an id.

**Idempotency**

R6. If `transfer` is given a `key`, the first successful call with that key is remembered. Calling
    again with the same key and the same `(src, dst, amount)` moves no money and returns the original
    transaction id, even if `src` could not afford the transfer any more and even if that transaction
    was reversed in the meantime. The same key with a different `(src, dst, amount)` raises
    `KeyConflict` (a subclass of `ValueError`) and changes nothing. A call that failed does not
    remember its key, so it can be retried later with the same key. Different keys are independent.

**Holds**

R7. `hold(name, amount)` reserves funds and returns a hold id. Hold ids are ints counting up from 1,
    separate from transaction ids. It raises `InsufficientFunds` if `amount` is more than
    `available(name)`. A hold lowers `available` but not `balance`, and `withdraw` and `transfer` must
    respect it (R3, R4). `release(hold_id)` ends a hold and gives the funds back to `available`.
    `release` of an unknown or already finished hold raises `KeyError`.
R8. `capture(hold_id, dst=None)` ends the hold and posts its amount: as a withdrawal from the holder if
    `dst` is `None`, otherwise as a transfer from the holder to `dst`. It returns the transaction id.
    A capture never fails for lack of funds, and the captured amount counts only once (the hold is
    gone afterwards). An unknown or already finished hold raises `KeyError`. If `dst` is unknown
    (`KeyError`) or is the holder (`ValueError`), the call fails and the hold stays active.

**Reversal and history**

R9. `reverse(txn_id)` undoes a transfer (including a capture to a `dst`) by posting a new transaction
    that moves the same amount from the original `dst` back to the original `src`, and returns its id.
    It raises `InsufficientFunds` if the amount is more than `available(dst)`, in which case nothing
    changes and the transfer can still be reversed later. Reversing an unknown id raises `KeyError`.
    Reversing a deposit, a withdrawal, a reversal, or a transfer that was already reversed raises
    `ValueError`.
R10. `history(name)` returns a list of `(txn_id, delta)` tuples in posting order, one per transaction
    that touched the account (negative delta for money out). The deltas add up to `balance(name)`.
    `total()` returns the sum of all balances. `InsufficientFunds` is an `Exception` subclass exported
    from `ledgerkit` next to `Ledger` and `KeyConflict`.

Standard library only. Existing tests are in `tests/`.
