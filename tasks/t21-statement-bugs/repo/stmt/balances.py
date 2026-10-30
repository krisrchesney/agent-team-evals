"""Account balances at a point in time."""


def balance_before(store, account_id, moment):
    """Sum of posted transactions strictly before `moment`."""
    return sum(t.amount_cents for t in store.all(account_id)
               if t.status == "posted" and t.posted_at < moment)
