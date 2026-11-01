Documents in `finder` need an author. Add an `author` field to them (the name of the person who wrote the document, like "Mary Ann Smith") and make it searchable like the other fields:

- `author:smith` in a query, and `fields=["author"]` in a search;
- plain queries (no field) find it too, but a match in the author ranks below the same match in the title;
- highlights, saved documents (dicts and JSON lines) and index snapshots carry it;
- the command line's `--field` option accepts it.

Documents saved before this change have no author. Existing behaviour must keep working. Use only the Python standard library. Existing tests are in `tests/`.
