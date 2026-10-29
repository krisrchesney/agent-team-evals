import os
import tempfile
import unittest
from unittest import mock

import confkit
from confkit import DEFAULTS, ConfigError, load

INI = """\
[server]
host = files.example
port = 9000
debug = no

[database]
pool_size = 7

[extra]
color = blue
"""


class HiddenEnvOverrides(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)
        self.addCleanup(os.remove, self.path)
        self.write(INI)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # Requirement 1: signature, precedence, fresh dict
    def test_no_file_no_env_is_defaults(self):
        self.assertEqual(load(env={}), DEFAULTS)
        self.assertEqual(load(None, {}), DEFAULTS)

    def test_precedence_env_over_file_over_defaults(self):
        s = load(self.path, env={"APP_SERVER__PORT": "9100"})
        self.assertEqual(s["server"]["port"], 9100)                 # env beats file
        self.assertEqual(s["server"]["host"], "files.example")       # file beats default
        self.assertEqual(s["database"]["url"], "sqlite:///app.db")   # default
        self.assertEqual(s["database"]["pool_size"], 7)

    def test_env_without_file(self):
        s = load(env={"APP_DATABASE__URL": "postgres://db/x"})
        self.assertEqual(s["database"]["url"], "postgres://db/x")

    def test_env_none_uses_os_environ(self):
        with mock.patch.dict(os.environ, {"APP_SERVER__PORT": "8123"}, clear=True):
            self.assertEqual(load()["server"]["port"], 8123)
            self.assertEqual(load(self.path)["server"]["port"], 8123)

    def test_defaults_not_mutated_and_fresh_dict(self):
        before = {s: dict(v) for s, v in DEFAULTS.items()}
        a = load(self.path, env={"APP_SERVER__HOST": "h"})
        a["server"]["port"] = -1
        b = load(env={})
        self.assertEqual(DEFAULTS, before)
        self.assertEqual(b["server"]["port"], 8000)
        self.assertNotIn("extra", DEFAULTS)

    # Requirement 2: variable naming
    def test_naming_with_underscored_key(self):
        s = load(env={"APP_DATABASE__POOL_SIZE": "12", "APP_DATABASE__TIMEOUT": "2.5"})
        self.assertEqual(s["database"]["pool_size"], 12)
        self.assertEqual(s["database"]["timeout"], 2.5)

    def test_lowercase_and_unprefixed_names_ignored(self):
        s = load(env={"app_server__port": "1", "SERVER__PORT": "2", "APP_server__port": "3"})
        self.assertEqual(s["server"]["port"], 8000)

    # Requirement 3: only DEFAULTS keys can be overridden
    def test_unknown_variables_ignored(self):
        env = {
            "APP_SERVER_PORT": "1",          # wrong separator
            "APP_NOPE__PORT": "2",           # unknown section
            "APP_SERVER__WORKERS": "3",      # unknown key
            "APP_EXTRA__COLOR": "red",       # key only the file defines
        }
        s = load(self.path, env=env)
        self.assertEqual(s["server"]["port"], 9000)
        self.assertNotIn("workers", s["server"])
        self.assertNotIn("nope", s)
        self.assertEqual(s["extra"]["color"], "blue")

    # Requirement 4: type conversion
    def test_bool_words_from_env(self):
        for word, want in [("1", True), ("TRUE", True), (" yes ", True), ("On", True),
                           ("0", False), ("False", False), ("no", False), (" OFF", False)]:
            with self.subTest(word=word):
                self.assertIs(load(env={"APP_SERVER__DEBUG": word})["server"]["debug"], want)

    def test_false_from_env_overrides_true_file(self):
        self.write("[server]\ndebug = true\n")
        self.assertIs(load(self.path, env={})["server"]["debug"], True)
        self.assertIs(load(self.path, env={"APP_SERVER__DEBUG": "false"})["server"]["debug"], False)

    def test_bool_from_file(self):
        self.assertIs(load(self.path, env={})["server"]["debug"], False)  # "no" in INI
        self.write("[server]\ndebug = off\n")
        self.assertIs(load(self.path, env={})["server"]["debug"], False)

    def test_numbers_strip_whitespace_and_str_kept_as_given(self):
        s = load(env={"APP_SERVER__PORT": " 42 ", "APP_SERVER__HOST": " spaced "})
        self.assertEqual(s["server"]["port"], 42)
        self.assertIsInstance(s["server"]["port"], int)
        self.assertEqual(s["server"]["host"], " spaced ")

    def test_file_only_keys_raw_strings(self):
        self.write("[extra]\nretries = 3\n")
        self.assertEqual(load(self.path, env={})["extra"]["retries"], "3")

    # Requirement 5: errors name their source
    def test_bad_env_value_names_variable(self):
        with self.assertRaises(ConfigError) as cm:
            load(self.path, env={"APP_SERVER__PORT": "eighty"})
        self.assertIn("APP_SERVER__PORT", str(cm.exception))
        with self.assertRaises(ConfigError) as cm:
            load(env={"APP_SERVER__DEBUG": "maybe"})
        self.assertIn("APP_SERVER__DEBUG", str(cm.exception))

    def test_bad_file_value_names_key(self):
        self.write("[server]\nport = lots\n")
        with self.assertRaises(ConfigError) as cm:
            load(self.path, env={})
        self.assertIn("server.port", str(cm.exception))
        self.write("[server]\ndebug = perhaps\n")
        with self.assertRaises(ConfigError) as cm:
            load(self.path, env={})
        self.assertIn("server.debug", str(cm.exception))

    def test_config_error_is_value_error(self):
        self.assertTrue(issubclass(confkit.ConfigError, ValueError))

    # Requirement 6: empty or whitespace-only variables count as not set
    def test_empty_env_keeps_file_value(self):
        s = load(self.path, env={"APP_SERVER__PORT": "", "APP_SERVER__HOST": "",
                                 "APP_DATABASE__POOL_SIZE": "   "})
        self.assertEqual(s["server"]["port"], 9000)
        self.assertEqual(s["server"]["host"], "files.example")
        self.assertEqual(s["database"]["pool_size"], 7)

    def test_empty_env_keeps_default_and_no_error(self):
        s = load(env={"APP_SERVER__DEBUG": "", "APP_DATABASE__TIMEOUT": " \t",
                      "APP_DATABASE__URL": ""})
        self.assertIs(s["server"]["debug"], False)
        self.assertEqual(s["database"]["timeout"], 30.0)
        self.assertEqual(s["database"]["url"], "sqlite:///app.db")


if __name__ == "__main__":
    unittest.main()
