import os
import tempfile
import unittest

from confkit import load


class TestLoad(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)
        self.addCleanup(os.remove, self.path)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_file_overrides_defaults(self):
        self.write("[server]\nport = 9000\n")
        s = load(self.path)
        self.assertEqual(s["server"]["port"], 9000)
        self.assertEqual(s["server"]["host"], "127.0.0.1")

    def test_unknown_keys_kept(self):
        self.write("[extra]\ncolor = blue\n")
        self.assertEqual(load(self.path)["extra"]["color"], "blue")


if __name__ == "__main__":
    unittest.main()
