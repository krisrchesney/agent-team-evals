import unittest

from pkgplan import Constraint, Registry, Version, resolve


class TestBasics(unittest.TestCase):
    def test_version_order(self):
        self.assertLess(Version("1.2.9"), Version("1.10.0"))

    def test_constraint_range(self):
        c = Constraint(">=1.0.0,<2.0.0")
        self.assertTrue(c.matches(Version("1.5.0")))
        self.assertFalse(c.matches(Version("2.0.0")))

    def test_resolve_picks_highest(self):
        r = Registry()
        r.add("web", "1.0.0")
        r.add("web", "1.5.0")
        r.add("web", "2.0.0")
        self.assertEqual([str(p.version) for p in resolve(r, ["web<2.0.0"])], ["1.5.0"])

    def test_resolve_follows_dependencies(self):
        r = Registry()
        r.add("app", "1.0.0", deps={"lib": ">=1.0.0"})
        r.add("lib", "1.0.0")
        self.assertEqual([p.name for p in resolve(r, ["app"])], ["app", "lib"])


if __name__ == "__main__":
    unittest.main()
