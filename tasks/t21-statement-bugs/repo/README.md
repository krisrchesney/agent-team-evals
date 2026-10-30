# stmt

Builds customers' monthly account statements from the transaction feed.

```python
from stmt import Account, TxnStore, build_statement, render
statement = build_statement(store, account, 2024, 5)
print(render(statement))
```

What a statement must contain is defined in `docs/STATEMENTS.md`. How transactions arrive (and why
the same transaction can arrive more than once) is in `docs/FEED.md`.

Run the tests with `python -m unittest discover -s tests -t .`.
