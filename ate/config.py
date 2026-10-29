"""Load configs/*.json, agent role files, prompt templates and output schemas."""
import json
import re
from pathlib import Path

from . import REPO_ROOT

CONFIG_DIR = REPO_ROOT / "configs"


def load_defaults(path=None):
    return json.loads(Path(path or CONFIG_DIR / "defaults.json").read_text(encoding="utf-8"))


def load_config(config_id):
    cfg = json.loads((CONFIG_DIR / f"{config_id}.json").read_text(encoding="utf-8"))
    if cfg["id"] != config_id:
        raise ValueError(f"{config_id}.json has id {cfg['id']!r}")
    return cfg


def list_configs():
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json") if p.stem != "defaults")


def load_prompt(name):
    return (CONFIG_DIR / "prompts" / name).read_text(encoding="utf-8")


def load_schema(name):
    return json.loads((CONFIG_DIR / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.S)


def parse_agent_md(text):
    """Parse a .claude/agents/*.md file: simple `key: value` frontmatter plus a body prompt."""
    m = _FRONTMATTER.match(text)
    if not m:
        raise ValueError("agent file has no --- frontmatter ---")
    meta = {}
    for line in m.group(1).splitlines():
        if line.strip() and ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    meta["prompt"] = m.group(2).strip()
    if "tools" in meta:
        meta["tools"] = [t.strip() for t in meta["tools"].split(",") if t.strip()]
    return meta


def load_agents(agents_dir):
    """Return {name: {description, prompt, tools}} in the shape `claude --agents` expects."""
    if not agents_dir:
        return {}
    out = {}
    for path in sorted((REPO_ROOT / agents_dir).glob("*.md")):
        meta = parse_agent_md(path.read_text(encoding="utf-8"))
        name = meta.pop("name", path.stem)
        out[name] = {k: v for k, v in meta.items() if k in ("description", "prompt", "tools", "model")}
    return out
