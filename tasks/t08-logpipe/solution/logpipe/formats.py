"""Output formats. FORMATS maps a name to a function record -> str."""
import json

from .errors import ConfigError


def _value(text):
    return f'"{text}"' if text == "" or any(c.isspace() for c in text) else text


def format_text(rec):
    line = f"{rec.ts} {rec.level} {rec.msg}"
    if rec.fields:
        line += " | " + " ".join(f"{k}={_value(v)}" for k, v in rec.fields.items())
    return line


def format_json(rec):
    return json.dumps({"ts": rec.ts, "level": rec.level, "msg": rec.msg, "fields": rec.fields})


FORMATS = {"text": format_text, "json": format_json}


def get_format(name):
    try:
        return FORMATS[name]
    except KeyError:
        raise ConfigError(f"unknown format '{name}'") from None
