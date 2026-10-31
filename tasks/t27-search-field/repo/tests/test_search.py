import unittest

from finder import Searcher, make
from finder.errors import QueryError
from finder.query import parse, canon


def build():
    s = Searcher()
    s.add(make("d1", "Running shoes", "Light shoes for running on roads", ["sport", "gear"]))
    s.add(make("d2", "Garden tools", "Spades and rakes for the garden", ["home"]))
    s.add(make("d3", "Trail guide", "Where to run near the lake", ["sport"]))
    return s


class SearchTest(unittest.TestCase):
    def test_stemmed_text_fields(self):
        ids = [h.id for h in build().search("runs").hits]
        self.assertEqual(ids, ["d1", "d3"])

    def test_title_outranks_body(self):
        ids = [h.id for h in build().search("shoes").hits]
        self.assertEqual(ids[0], "d1")

    def test_field_prefix_and_phrase(self):
        s = build()
        self.assertEqual([h.id for h in s.search("tags:sport").hits], ["d1", "d3"])
        self.assertEqual([h.id for h in s.search('title:"garden tools"').hits], ["d2"])

    def test_tags_are_not_stemmed(self):
        self.assertEqual(build().search("tags:sports").total, 0)

    def test_exclusion_and_or(self):
        s = build()
        self.assertEqual([h.id for h in s.search("sport -gear").hits], ["d3"])
        self.assertEqual(sorted(h.id for h in s.search("garden OR lake").hits), ["d2", "d3"])

    def test_unknown_field_is_an_error(self):
        with self.assertRaises(QueryError):
            build().search("colour:red")

    def test_cache_hits_and_invalidation(self):
        s = build()
        s.search("shoes")
        s.search("shoes")
        self.assertEqual(s.cache.stats()["hits"], 1)
        s.add(make("d4", "More shoes"))
        self.assertEqual(s.search("shoes").total, 2)

    def test_highlight(self):
        hit = build().search("garden", highlight=True).hits[0]
        self.assertEqual(hit.highlights["title"], "<em>Garden</em> tools")

    def test_canon_ignores_spacing(self):
        self.assertEqual(canon(parse("a   b")), canon(parse("a b")))


if __name__ == "__main__":
    unittest.main()
