import os
import tempfile
import unittest
import warnings

from jobd.config import DeprecatedSettingWarning, SETTINGS, loader
from jobd.errors import ConfigError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        s = loader.load(environ={})
        self.assertEqual((s.queue_workers, s.queue_size, s.log_level), (4, 1000, "info"))

    def test_environment_beats_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "c.json")
            with open(path, "w") as handle:
                handle.write('{"retry_limit": 7}')
            s = loader.load(path=path, environ={"JOBD_RETRY_LIMIT": "2"})
        self.assertEqual(s.retry_limit, 2)

    def test_range_errors_name_the_setting(self):
        with self.assertRaises(ConfigError) as ctx:
            loader.load(environ={"JOBD_RETRY_LIMIT": "99"})
        self.assertIn("retry_limit", str(ctx.exception))

    def test_loglevel_is_the_old_name_of_log_level(self):
        with self.assertWarns(DeprecatedSettingWarning) as ctx:
            s = loader.load(environ={"JOBD_LOGLEVEL": "debug"})
        self.assertEqual(s.log_level, "debug")
        self.assertIn("'loglevel'", str(ctx.warning))
        self.assertIn("'log_level'", str(ctx.warning))

    def test_loglevel_attribute_still_reads(self):
        with self.assertWarns(DeprecatedSettingWarning):
            self.assertEqual(loader.load(environ={}).loglevel, "info")

    def test_every_setting_is_documented(self):
        with open(os.path.join(ROOT, "docs", "settings.md"), encoding="utf-8") as handle:
            text = handle.read()
        for name in SETTINGS:
            self.assertIn(f"`{name}`", text, f"{name} is missing from docs/settings.md")

    def test_example_configs_load_without_warnings(self):
        for name in ("jobd.json", "jobd.ini"):
            with warnings.catch_warnings():
                warnings.simplefilter("error", DeprecatedSettingWarning)
                loader.load(path=os.path.join(ROOT, "examples", name), environ={})


if __name__ == "__main__":
    unittest.main()
