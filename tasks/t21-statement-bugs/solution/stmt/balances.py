"""Account balances at a point in time."""


def counted(store, account_id):
    """The transactions a statement counts: latest version of each, posted only."""
    return [t for t in store.current(account_id) if t.status == "posted"]


def balance_before(store, account_id, moment):
    """Sum of counted transactions strictly before `moment`."""
    return sum(t.amount_cents for t in counted(store, account_id) if t.posted_at < moment)
