"""Output formats. FORMATS maps a name to a function record -> str."""
import json

from .errors import ConfigError


def format_text(rec):
    return f"{rec.ts} {rec.level} {rec.msg}"


def format_json(rec):
    return json.dumps({"ts": rec.ts, "level": rec.level, "msg": rec.msg})


FORMATS = {"text": format_text, "json": format_json}


def get_format(name):
    try:
        return FORMATS[name]
    except KeyError:
        raise ConfigError(f"unknown format '{name}'") from None
