"""Stand-in user for clarify-first tasks.

A headless agent cannot ask the user anything, so a task whose request is ambiguous on purpose gets
one extra tool, `ask_user(question)`, served by a tiny local MCP server (server.py). It answers from
the task's hidden answers.json by keyword match (no model call) and logs every question, so "did the
agent ask the right thing" is measurable. This module holds the harness side: the --mcp-config file,
reading the log back into the run record, and the isolation check on the CLI's startup event.
"""
import json
import sys
from pathlib import Path

from .server import DEFAULT_ANSWER, load_answers  # noqa: F401  (re-exported for the harness)

SERVER_NAME = "ask_user"
TOOL_NAME = "ask_user"
# Added to --allowedTools so the call does not wait on a permission prompt (there is nobody to answer one).
ALLOWED_TOOL = f"mcp__{SERVER_NAME}__{TOOL_NAME}"
SERVER_FILE = Path(__file__).resolve().parent / "server.py"
LOG_NAME = "ask_user.jsonl"


def write_mcp_config(path, answers_path, log_path, default_answer=None):
    """Write the JSON for `--mcp-config`: one stdio server, run by this Python as a plain script."""
    args = [str(SERVER_FILE), "--answers", str(answers_path), "--log", str(log_path)]
    if default_answer:
        args += ["--default", default_answer]
    cfg = {"mcpServers": {SERVER_NAME: {"command": sys.executable, "args": args}}}
    Path(path).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return Path(path)


def read_log(log_path, skip=0):
    """Questions logged so far (after the first `skip` lines) as [{question, answer, matched}]."""
    p = Path(log_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[skip:]:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append({"question": ev.get("question", ""), "answer": ev.get("answer", ""),
                    "matched": ev.get("matched")})
    return out


def isolation_problems(mcp_servers, skills=None, slash_commands=None):
    """Check the startup event's `mcp_servers` when ask_user is on: a list of problems (empty = fine).

    Without --safe-mode these runs must also load no skills and no slash commands (non-empty lists are
    flagged). Only SERVER_NAME may be loaded, and it must be connected. Anything else is a leak of the personal
    setup; a missing or failed ask_user means the agent could not ask, so the run is not valid.
    """
    problems, found = [], False
    if skills:
        problems.append(f"skills loaded: {skills}")
    if slash_commands:
        problems.append(f"slash commands loaded: {slash_commands}")
    for srv in mcp_servers or []:
        name = srv.get("name") if isinstance(srv, dict) else str(srv)
        if name == SERVER_NAME:
            found = True
            status = srv.get("status") if isinstance(srv, dict) else None
            if status not in (None, "connected"):
                problems.append(f"{SERVER_NAME} server status {status!r}")
        else:
            problems.append(f"unexpected mcp server loaded: {srv}")
    if not found:
        problems.append(f"{SERVER_NAME} server not loaded")
    return problems
