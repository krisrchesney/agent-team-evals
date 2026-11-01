"""Hidden tests for t27-search-field. Every rule is stated in the prompt or shown by the code; see AUDIT.md."""
import io
import itertools
import json
import os
import tempfile
import unittest

from finder import Library, Searcher, make, schema, serializer, snapshot
from finder import bulk, cache, cli, reindex
from finder.errors import QueryError


def corpus():
    s = Searcher()
    s.add(make("a1", "Annual report", "Figures for the year", ["finance"], author="Mary Ann Smith"))
    s.add(make("a2", "Smith family history", "Genealogy notes", [], author="Bob Jones"))
    s.add(make("a3", "The Who live", "Concert notes", [], author="The Who"))
    s.add(make("a4", "Hughes biography", "A life in letters", [], author="Anne-Marie O'Neil"))
    s.add(make("a5", "Misc", "smith appears only in the body of this one"))
    return s


def ids(result):
    return [h.id for h in result.hits]


class TestDocuments(unittest.TestCase):
    def test_author_defaults_to_empty_and_is_cleaned_like_other_text(self):
        self.assertEqual(make("x").author, "")
        self.assertEqual(make("x", author="  Mary   Ann ").author, "Mary Ann")

    def test_to_dict_and_back(self):
        doc = make("x", "T", "B", ["t"], "2026-01-01", author="Mary Ann Smith")
        data = serializer.to_dict(doc)
        self.assertEqual(data["author"], "Mary Ann Smith")
        self.assertEqual(serializer.from_dict(data), doc)

    def test_dicts_saved_before_the_change_have_no_author(self):
        old = {"id": "x", "title": "T", "body": "B", "tags": ["t"], "updated": ""}
        self.assertEqual(serializer.from_dict(old).author, "")

    def test_json_lines_round_trip(self):
        docs = [make("x", "T", author="Mary Ann Smith"), make("y", "U")]
        text = serializer.dumps(docs)
        self.assertEqual(json.loads(text.splitlines()[0])["author"], "Mary Ann Smith")
        self.assertEqual(serializer.loads(text), docs)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.s = corpus()

    def test_author_prefix(self):
        self.assertEqual(ids(self.s.search("author:smith")), ["a1"])

    def test_every_word_of_the_name_is_searchable(self):
        self.assertEqual(ids(self.s.search("author:mary")), ["a1"])
        self.assertEqual(ids(self.s.search("author:ann")), ["a1"])

    def test_phrase_in_author(self):
        self.assertEqual(ids(self.s.search('author:"mary ann"')), ["a1"])
        self.assertEqual(ids(self.s.search('author:"ann mary"')), [])

    def test_author_search_ignores_case(self):
        self.assertEqual(ids(self.s.search("author:SMITH")), ["a1"])

    def test_names_are_not_stemmed(self):
        self.s.add(make("a6", "Poem", author="Ted Hughes"))
        self.assertEqual(ids(self.s.search("author:hughes")), ["a6"])
        self.assertEqual(ids(self.s.search("author:hugh")), [])
        self.assertEqual(ids(self.s.search("author:smiths")), [])

    def test_stop_words_in_names_are_kept(self):
        self.assertEqual(ids(self.s.search("author:the")), ["a3"])
        self.assertEqual(ids(self.s.search('author:"the who"')), ["a3"])

    def test_hyphens_and_apostrophes_split_words(self):
        self.assertEqual(ids(self.s.search("author:marie")), ["a4"])
        self.assertEqual(ids(self.s.search("author:neil")), ["a4"])
        self.assertEqual(ids(self.s.search('author:"o neil"')), ["a4"])

    def test_plain_query_finds_the_author(self):
        self.assertEqual(self.s.search("smith").total, 3)
        self.assertIn("a1", ids(self.s.search("smith")))

    def test_title_match_ranks_above_author_match(self):
        self.assertEqual(ids(self.s.search("smith"))[0], "a2")
        s = Searcher()
        s.add(make("a0", "Notes", author="Zed"))
        s.add(make("z9", "Zed", "Notes"))
        self.assertEqual(ids(s.search("zed")), ["z9", "a0"])

    def test_plain_phrase_matches_the_author(self):
        self.assertEqual(ids(self.s.search('"mary ann"')), ["a1"])

    def test_fields_option_limits_plain_terms_to_author(self):
        self.assertEqual(ids(self.s.search("smith", fields=["author"])), ["a1"])

    def test_fields_option_can_combine_author_and_title(self):
        self.assertEqual(ids(self.s.search("smith", fields=["title", "author"])), ["a2", "a1"])

    def test_excluding_an_author(self):
        self.assertEqual(sorted(ids(self.s.search("smith -author:smith"))), ["a2", "a5"])

    def test_or_across_authors(self):
        self.assertEqual(sorted(ids(self.s.search("author:jones OR author:smith"))), ["a1", "a2"])

    def test_replacing_a_document_reindexes_its_author(self):
        self.s.update(make("a1", "Annual report", author="Jane Doe"))
        self.assertEqual(ids(self.s.search("author:smith")), [])
        self.assertEqual(ids(self.s.search("author:doe")), ["a1"])

    def test_removing_a_document_removes_its_author(self):
        self.s.remove("a1")
        self.assertEqual(ids(self.s.search("author:smith")), [])

    def test_unknown_fields_are_still_errors(self):
        for bad in ("colour:red",):
            with self.assertRaises(QueryError):
                self.s.search(bad)
        with self.assertRaises(QueryError):
            self.s.search("smith", fields=["author", "nope"])

    def test_index_stats_cover_the_field(self):
        self.assertGreater(self.s.index.stats()["fields"]["author"]["terms"], 0)

    def test_reg_existing_fields_behave_as_before(self):
        self.assertEqual(ids(self.s.search("lives")), ["a3"])
        self.assertEqual(ids(self.s.search("tags:finance")), ["a1"])
        self.assertEqual(ids(self.s.search("tags:finances")), [])
        self.assertEqual(ids(self.s.search("title:reports")), ["a1"])


class TestCache(unittest.TestCase):
    def test_searches_in_the_author_field_are_cached(self):
        s = corpus()
        first = s.search("smith", fields=["author"])
        before = s.cache.stats()["hits"]
        second = s.search("smith", fields=["author"])
        self.assertEqual(s.cache.stats()["hits"], before + 1)
        self.assertEqual(ids(first), ids(second))

    def test_cached_results_do_not_leak_between_field_sets(self):
        s = corpus()
        for _ in range(2):
            self.assertEqual(ids(s.search("smith", fields=["title"])), ["a2"])
            self.assertEqual(ids(s.search("smith", fields=["author"])), ["a1"])
            self.assertEqual(ids(s.search("smith", fields=["body"])), ["a5"])

    def test_cache_forgets_when_an_author_changes(self):
        s = corpus()
        self.assertEqual(ids(s.search("author:smith")), ["a1"])
        s.update(make("a1", "Annual report", author="Jane Doe"))
        self.assertEqual(ids(s.search("author:smith")), [])

    def test_every_set_of_fields_has_its_own_mask(self):
        names = schema.field_names()
        masks = set()
        for size in range(1, len(names) + 1):
            for combo in itertools.combinations(names, size):
                masks.add(cache.fields_mask(list(combo)))
        self.assertEqual(len(masks), 2 ** len(names) - 1)
        self.assertEqual(cache.fields_mask(list(names)) & cache.fields_mask(["author"]), cache.fields_mask(["author"]))


class TestHighlight(unittest.TestCase):
    def test_author_is_highlighted_with_its_original_spelling(self):
        hits = {h.id: h for h in corpus().search("smith", highlight=True).hits}
        self.assertEqual(hits["a1"].highlights, {"author": "Mary Ann <em>Smith</em>"})
        self.assertEqual(hits["a2"].highlights, {"title": "<em>Smith</em> family history"})

    def test_prefixed_query_highlights_only_that_field(self):
        (hit,) = corpus().search("author:smith", highlight=True).hits
        self.assertEqual(hit.highlights, {"author": "Mary Ann <em>Smith</em>"})

    def test_reg_stemmed_fields_still_highlight(self):
        (hit,) = corpus().search("reports", highlight=True).hits
        self.assertEqual(hit.highlights, {"title": "Annual <em>report</em>"})


class TestSnapshots(unittest.TestCase):
    def test_round_trip_keeps_authors(self):
        data = snapshot.dump(corpus())
        self.assertIn("author", data["fields"])
        self.assertEqual({d["id"]: d["author"] for d in data["docs"]}["a1"], "Mary Ann Smith")
        again = snapshot.loads(snapshot.dumps(corpus()))
        self.assertEqual(ids(again.search("author:smith")), ["a1"])

    def test_snapshots_written_before_the_change_still_load(self):
        old = {"format": 2, "fields": ["title", "body", "tags"],
               "docs": [{"id": "x", "title": "Old", "body": "text", "tags": ["t"], "updated": ""}]}
        s = snapshot.load(old)
        self.assertEqual(ids(s.search("old")), ["x"])
        self.assertEqual(s.search("author:old").total, 0)

    def test_rebuild_matches(self):
        self.assertTrue(reindex.verify(corpus()))


class TestEntryPoints(unittest.TestCase):
    def test_library_and_bulk_load(self):
        lib = Library()
        lib.add({"id": "x", "title": "T", "author": "Mary Ann Smith"})
        report = bulk.load_jsonl(lib.searcher, '{"id": "y", "title": "U"}\n{"id": "z", "author": "Zed Smith"}\n')
        self.assertTrue(report.ok)
        self.assertEqual(sorted(ids(lib.search("author:smith"))), ["x", "z"])

    def test_command_line_field_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "docs.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(serializer.dumps(corpus().index.docs[i] for i in sorted(corpus().index.docs)))
            out = io.StringIO()
            code = cli.main(["search", "smith", "--docs", path, "--field", "author"], out)
            lines = out.getvalue().splitlines()
            self.assertEqual(code, 0)
            self.assertEqual(lines[0], "1 result(s)")
            self.assertTrue(lines[1].startswith("a1\t"))
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["search", "smith", "--docs", path, "--field", "nope"], io.StringIO())
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
