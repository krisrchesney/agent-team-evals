"""Load configs/*.json, agent role files, prompt templates and output schemas."""
import json
import re
from pathlib import Path

from . import REPO_ROOT

CONFIG_DIR = REPO_ROOT / "configs"


def load_defaults(path=None):
    return json.loads(Path(path or CONFIG_DIR / "defaults.json").read_text(encoding="utf-8"))


STAGE_KEYS = {"name", "agent", "prompt", "mode", "schema", "only_if", "foreach",
              "tools", "allowed_tools", "settings"}  # the last three are optional per-stage overrides

# A per-stage settings file must not be able to change who is billed, which model runs, or how
# permissions work: those are fixed for every config so only the team structure differs.
_FORBIDDEN_SETTINGS_KEYS = {"apikeyhelper", "model", "forceloginmethod", "forceloginorguuid", "awsauthrefresh",
                            "awscredentialexport", "gcpauthrefresh", "forcelogingatewayurl", "allowedproviders",
                            "disableclaudeaiconnectors", "enabledplugins", "mcpservers"}
_FORBIDDEN_ENV_PREFIXES = ("ANTHROPIC_", "CLAUDE_", "AWS_", "GOOGLE_", "ENABLE_CLAUDEAI")


def settings_path(rel):
    """Resolve a stage's `settings` value to a file inside configs/ (anything else is an error)."""
    path = (CONFIG_DIR / rel).resolve()
    if CONFIG_DIR.resolve() not in path.parents:
        raise ValueError(f"settings file {rel!r} must be inside configs/")
    if not path.is_file():
        raise ValueError(f"settings file {rel!r} does not exist")
    return path


def check_settings_file(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: settings must be a JSON object")
    bad = [k for k in data if k.lower() in _FORBIDDEN_SETTINGS_KEYS]
    if bad:
        raise ValueError(f"{path}: settings may not set {bad} (auth, model, plugins and MCP are fixed for all configs)")
    env = data.get("env") or {}
    bad_env = [k for k in env if k.upper().startswith(_FORBIDDEN_ENV_PREFIXES)]
    if bad_env:
        raise ValueError(f"{path}: settings env may not set {bad_env}")
    if "bypasspermissions" in json.dumps(data).lower():
        raise ValueError(f"{path}: settings may not enable bypassPermissions")


def validate_stage(stage, config_id="?"):
    where = f"config {config_id} stage {stage.get('name', '?')!r}"
    unknown = set(stage) - STAGE_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown stage keys {sorted(unknown)}")
    if "tools" in stage and not (isinstance(stage["tools"], str) and stage["tools"].strip()):
        raise ValueError(f"{where}: tools must be a non-empty comma-separated string")
    if "allowed_tools" in stage:
        at = stage["allowed_tools"]
        if not (isinstance(at, list) and at and all(isinstance(x, str) and x for x in at)):
            raise ValueError(f"{where}: allowed_tools must be a non-empty list of strings")
    if "settings" in stage:
        if not isinstance(stage["settings"], str):
            raise ValueError(f"{where}: settings must be a path string")
        check_settings_file(settings_path(stage["settings"]))


def load_config(config_id):
    cfg = json.loads((CONFIG_DIR / f"{config_id}.json").read_text(encoding="utf-8"))
    if cfg["id"] != config_id:
        raise ValueError(f"{config_id}.json has id {cfg['id']!r}")
    for stage in cfg["stages"]:
        validate_stage(stage, config_id)
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


def check_agent_models(agents, model):
    """A role's `model:` frontmatter would override --model for that stage, quietly running one role
    on a different (often pricier) model than the rest. Roles may omit it, say `inherit`, or match."""
    for name, agent in agents.items():
        if agent.get("model") not in (None, "inherit", model):
            raise ValueError(f"agent {name!r} sets model {agent['model']!r}; the sweep model is {model!r}. "
                             f"Remove the model line (or use --model {agent['model']} for the whole sweep).")


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
