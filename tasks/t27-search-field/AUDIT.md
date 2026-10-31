# t27-search-field: where each hidden-test rule is shown

The repo is a 3,100-line search library. A new indexed field has to be added in seven places that do
not reference each other; each one lists the existing fields by name. This file is outside `repo/`,
so agents never see it.

| Test group | Rule | Shown by (repo/) |
|---|---|---|
| `TestDocuments` | `author` is a trimmed, whitespace-collapsed string, default `""`; dicts and JSON lines carry it; old dicts without it load | prompt; `documents.make` / `clean_text`; `serializer.from_dict` docstring ("accepts dicts written by older versions") and its `.get(..., default)` calls |
| indexing tests (`test_author_prefix`, `test_replacing_...`, `test_removing_...`, `test_index_stats_...`) | the field is indexed: listed in `schema.FIELDS` and in `documents.field_values` (what is indexed) | `schema.py`, `documents.field_values`, `index.py` |
| `test_names_are_not_stemmed`, `test_stop_words_in_names_are_kept`, `test_hyphens_and_apostrophes_split_words` | a person's name uses the `words` analyzer, not `text` (no stemming, stop words kept) | `analysis/analyzers.py` docstring: `words` = "short free-form values ... can be found exactly as it was typed"; `text` = prose; prompt says author is a person's name |
| `test_author_prefix`, `test_phrase_in_author`, `test_author_search_ignores_case`, `test_every_word_...`, `test_excluding_...`, `test_or_across_...` | `author:` is accepted by the query parser | `query/parser.py` `KNOWN_FIELDS` and the unknown-field `QueryError`; prompt |
| `test_title_match_ranks_above_author_match` | the author boost is below the title boost (3.0); the test includes an id-order tie-break trap | prompt ("ranks below the same match in the title"); `schema.FIELDS` boosts |
| `test_plain_query_finds_the_author`, `test_plain_phrase_...` | plain terms search every field of `schema.default_fields()` | `schema.default_fields`, `search.py` |
| `test_fields_option_*`, `test_unknown_fields_are_still_errors` | `fields=["author"]` accepted; unknown names rejected | `search._check_fields`; prompt |
| `TestCache` | the cache key must tell field sets apart: `FIELD_BITS` needs a fresh, distinct bit for `author` (a missing entry raises `KeyError` on `fields=["author"]`; a reused bit mixes results) | `cache.py` `FIELD_BITS`, `fields_mask`, `make_key` |
| `TestHighlight` | `HIGHLIGHT_FIELDS` includes `author`; marked text keeps its original spelling | `highlight.py`; prompt ("highlights ... carry it") |
| `TestSnapshots` | snapshots store the fields and documents through the serializer; old snapshots still load | `snapshot.py` `load` docstring; `serializer` |
| `test_command_line_field_option` | the CLI's `--field` choices list the fields | `cli.py` `FIELD_CHOICES`; prompt |
| `test_library_and_bulk_load` | dict/bulk entry points go through the serializer | `library.py`, `bulk.py` |
| `test_reg_*` | existing fields keep stemming / no-stemming behaviour | `tests/test_search.py` |

What makes it hard: the field name appears in `schema.py`, `documents.py` (twice), `serializer.py`
(three places), `query/parser.py`, `cache.py`, `highlight.py` and `cli.py`. Any one missed fails a
group and nothing in the code connects them: only a search for `"tags"` across the repo finds all of
them. The analyzer choice (`words`, not `text`) is a judgement call that the analyzer docstrings settle.
