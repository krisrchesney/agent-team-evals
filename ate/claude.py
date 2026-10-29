"""Build and run one headless `claude -p` stage, and parse its cost/token data.

We use `--output-format stream-json --verbose`: every event goes to a log file (the transcript,
useful for "why did this run fail?"), and the last event, `type: "result"`, is the same object
`--output-format json` would print: total_cost_usd, usage, num_turns, duration_ms, subtype, ...
"""
import glob
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


def find_claude():
    """CLAUDE_BIN env var, then PATH, then the desktop app's bundled CLI (newest version)."""
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    found = shutil.which("claude")
    if found:
        return found
    appdata = os.environ.get("APPDATA", "")
    hits = glob.glob(os.path.join(appdata, "Claude", "claude-code", "*", "*", "claude.exe"))
    if hits:
        return max(hits, key=lambda p: _version_key(Path(p).parent.parent.name))
    return None


def _version_key(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))


def claude_version(binary):
    if not binary:
        return None
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


@dataclass
class StageSpec:
    name: str
    prompt: str
    cwd: Path
    log_path: Path
    model: str
    max_turns: int
    budget_usd: float
    timeout_s: int
    permission_mode: str
    tools: str
    allowed_tools: list
    bare: bool = True
    effort: str = None
    agent: str = None
    agents_file: Path = None
    json_schema: dict = None


@dataclass
class StageResult:
    name: str
    agent: str
    exit_code: int
    subtype: str = None
    is_error: bool = True
    cost_usd: float = 0.0
    tokens: dict = field(default_factory=lambda: dict(input=0, output=0, cache_read=0, cache_creation=0))
    model_usage: dict = field(default_factory=dict)
    num_turns: int = 0
    duration_s: float = 0.0
    duration_api_s: float = 0.0
    session_id: str = None
    result_text: str = ""
    structured: dict = None
    timed_out: bool = False
    error: str = None
    command: list = None

    def as_record(self):
        d = dict(self.__dict__)
        d.pop("result_text")
        d["result_excerpt"] = (self.result_text or "")[:500]
        return d


def build_command(binary, spec):
    """argv for one stage. The prompt itself goes on stdin (keeps variadic flags from eating it)."""
    cmd = [binary or "claude", "-p",
           "--output-format", "stream-json", "--verbose",
           "--model", spec.model,
           "--max-turns", str(spec.max_turns),
           "--max-budget-usd", f"{spec.budget_usd:.2f}",
           "--permission-mode", spec.permission_mode,
           "--permission-prompts", "none",
           "--no-session-persistence",
           "--tools", spec.tools,
           "--allowedTools", ",".join(spec.allowed_tools)]
    if spec.bare:
        cmd.append("--bare")
    if spec.effort:
        cmd += ["--effort", spec.effort]
    if spec.agents_file:
        cmd += ["--agents", str(spec.agents_file)]
    if spec.agent:
        cmd += ["--agent", spec.agent]
    if spec.json_schema:
        cmd += ["--json-schema", json.dumps(spec.json_schema, separators=(",", ":"))]
    return cmd


def run_stage(binary, spec, fake=None):
    """Run one stage. `fake` is a callable(spec) -> list of events, used by --dry-run."""
    cmd = build_command(binary, spec)
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    res = StageResult(name=spec.name, agent=spec.agent, exit_code=-1, command=_redact(cmd))
    if fake is not None:
        events = fake(spec)
        spec.log_path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        res.exit_code = 0
    else:
        env = dict(os.environ)
        try:
            with open(spec.log_path, "w", encoding="utf-8") as log:
                proc = subprocess.run(cmd, cwd=spec.cwd, input=spec.prompt, stdout=log,
                                      stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                      errors="replace", timeout=spec.timeout_s, env=env)
            res.exit_code = proc.returncode
            if proc.stderr.strip():
                res.error = proc.stderr.strip()[-2000:]
        except subprocess.TimeoutExpired:
            res.timed_out = True
            res.error = f"stage timed out after {spec.timeout_s}s"
        except OSError as exc:
            res.error = f"could not start claude: {exc}"
    res.duration_s = round(time.monotonic() - start, 2)
    apply_result_event(res, read_result_event(spec.log_path))
    return res


def read_result_event(log_path):
    """Last `type: result` event in a stream-json log, or None."""
    if not Path(log_path).exists():
        return None
    last = None
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                last = ev
    return last


def apply_result_event(res, ev):
    if not ev:
        res.error = res.error or "no result event in output"
        return
    usage = ev.get("usage") or {}
    res.subtype = ev.get("subtype")
    res.is_error = bool(ev.get("is_error", res.subtype != "success"))
    res.cost_usd = float(ev.get("total_cost_usd") or 0.0)
    res.tokens = {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
        "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
    }
    res.model_usage = ev.get("modelUsage") or {}
    res.num_turns = int(ev.get("num_turns") or 0)
    res.duration_api_s = round((ev.get("duration_api_ms") or 0) / 1000, 2)
    res.session_id = ev.get("session_id")
    res.result_text = ev.get("result") or ""
    so = ev.get("structured_output")
    if so is None and res.result_text.strip().startswith("{"):
        try:
            so = json.loads(res.result_text)
        except json.JSONDecodeError:
            so = None
    res.structured = so


def _redact(cmd):
    """Keep the logged argv readable: drop the (long) JSON schema body."""
    out = list(cmd)
    if "--json-schema" in out:
        out[out.index("--json-schema") + 1] = "<schema>"
    return out


def log_mentions(log_path, needles):
    """Which needles appear anywhere in the transcript (cheap hidden-test leak check)."""
    if not Path(log_path).exists():
        return []
    text = Path(log_path).read_text(encoding="utf-8", errors="replace").lower()
    return [n for n in needles if n.lower() in text]
