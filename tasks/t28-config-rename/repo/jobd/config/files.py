"""Reading settings from a JSON or INI file."""
import configparser
import json
import os

from ..errors import ConfigError

SECTION = "jobd"


def read(path):
    """Raw values from the file. The format follows the extension: .json, or .ini / .cfg."""
    if not os.path.exists(path):
        raise ConfigError(f"no such config file {path!r}", field="config")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _read_json(path)
    if ext in (".ini", ".cfg"):
        return _read_ini(path)
    raise ConfigError(f"unsupported config file type {ext!r}", field="config")


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path}: {exc.msg} (line {exc.lineno})", field="config") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object", field="config")
    return data


def _read_ini(path):
    parser = configparser.ConfigParser()
    parser.optionxform = str
    with open(path, encoding="utf-8") as handle:
        try:
            parser.read_file(handle)
        except configparser.Error as exc:
            raise ConfigError(f"{path}: {exc}", field="config") from None
    if not parser.has_section(SECTION):
        return {}
    return dict(parser.items(SECTION))
