"""Stdio MCP server with one tool, `ask_user(question)`. Standard library only, one file.

The harness starts it as `python server.py --answers <answers.json> --log <jsonl>` (it runs as a plain
script, so it must not import from the rest of ate/). Protocol: newline-delimited JSON-RPC 2.0 on
stdin/stdout, which is how Claude Code speaks to a stdio MCP server.

answers.json (hidden: it lives in the task folder, outside repo/):
  {"default": "No preference; use your judgment.",           optional
   "answers": [{"id": "currency", "keywords": ["currency", "euro"], "answer": "Whole cents, USD only."}]}
A question matches an entry when any of its keywords occurs in it, case-insensitive, at the start of a
word ("currenc" matches "currencies"; "id" does not match "side"). A keyword may be several words. With
several matching entries the one with the most distinct keyword hits wins, then the first listed.
No match: the default answer.
"""
import argparse
import json
import re
import sys
import time

DEFAULT_ANSWER = "No preference; use your judgment."
PROTOCOL_VERSION = "2024-11-05"
TOOL = {
    "name": "ask_user",
    "description": ("Ask the person who wrote the request one question when something is genuinely "
                    "unclear. Ask one specific question at a time. If they have no preference, you "
                    "are told so and should use your judgment."),
    "inputSchema": {"type": "object",
                    "properties": {"question": {"type": "string", "description": "One specific question."}},
                    "required": ["question"]},
}


def load_answers(path):
    """Parse and validate an answer sheet: returns {"default": str, "answers": [...]}. Raises ValueError."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("answers"), list):
        raise ValueError(f"{path}: need an object with an 'answers' list")
    seen = set()
    for i, entry in enumerate(data["answers"]):
        where = f"{path}: answers[{i}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{where} is not an object")
        kws = entry.get("keywords")
        if not (isinstance(kws, list) and kws and all(isinstance(k, str) and k.strip() for k in kws)):
            raise ValueError(f"{where} needs a non-empty 'keywords' list of strings")
        if not (isinstance(entry.get("answer"), str) and entry["answer"].strip()):
            raise ValueError(f"{where} needs a non-empty 'answer' string")
        ident = entry.setdefault("id", f"a{i + 1}")
        if ident in seen:
            raise ValueError(f"{where}: duplicate id {ident!r}")
        seen.add(ident)
    default = data.get("default", DEFAULT_ANSWER)
    if not (isinstance(default, str) and default.strip()):
        raise ValueError(f"{path}: 'default' must be a non-empty string")
    return {"default": default, "answers": data["answers"]}


def _hits(question, keywords):
    q = question.lower()
    n = 0
    for k in set(keywords):
        words = re.escape(" ".join(k.lower().split())).replace(r"\ ", r"\s+")
        if re.search(r"(?<![a-z0-9])" + words, q):
            n += 1
    return n


def match_answer(sheet, question):
    """(answer, matched entry id or None)."""
    best, best_hits = None, 0
    for entry in sheet["answers"]:
        n = _hits(question, entry["keywords"])
        if n > best_hits:
            best, best_hits = entry, n
    if best is None:
        return sheet["default"], None
    return best["answer"], best["id"]


def _ok(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _err(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


class Server:
    def __init__(self, sheet, log_path=None):
        self.sheet = sheet
        self.log_path = log_path

    def _log(self, question, answer, matched):
        if not self.log_path:
            return
        rec = {"t": round(time.time(), 3), "question": question, "answer": answer, "matched": matched}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec) + "\n")

    def handle(self, msg):
        """One JSON-RPC message in, the reply dict out (None for notifications)."""
        mid, method = msg.get("id"), msg.get("method")
        if mid is None:  # notification (e.g. notifications/initialized): no reply
            return None
        if method == "initialize":
            ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
            return _ok(mid, {"protocolVersion": ver, "capabilities": {"tools": {}},
                             "serverInfo": {"name": "ask_user", "version": "1.0"}})
        if method == "ping":
            return _ok(mid, {})
        if method == "tools/list":
            return _ok(mid, {"tools": [TOOL]})
        if method == "tools/call":
            params = msg.get("params") or {}
            if params.get("name") != TOOL["name"]:
                return _err(mid, -32602, f"unknown tool {params.get('name')!r}")
            question = (params.get("arguments") or {}).get("question")
            if not isinstance(question, str) or not question.strip():
                return _ok(mid, {"content": [{"type": "text", "text": "Give a non-empty 'question'."}],
                                 "isError": True})
            answer, matched = match_answer(self.sheet, question)
            self._log(question, answer, matched)
            return _ok(mid, {"content": [{"type": "text", "text": answer}], "isError": False})
        return _err(mid, -32601, f"method not found: {method}")


def serve(server, stdin, stdout):
    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
            reply = server.handle(msg) if isinstance(msg, dict) else _err(None, -32600, "invalid request")
        except json.JSONDecodeError:
            reply = _err(None, -32700, "parse error")
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def main(argv=None):
    ap = argparse.ArgumentParser(description="ask_user stand-in MCP server")
    ap.add_argument("--answers", required=True)
    ap.add_argument("--log")
    ap.add_argument("--default", help="override the sheet's default answer")
    args = ap.parse_args(argv)
    try:
        sheet = load_answers(args.answers)
    except (OSError, ValueError) as exc:
        print(f"ask_user: {exc}", file=sys.stderr)
        return 2
    if args.default:
        sheet["default"] = args.default
    # Fixed UTF-8 and "\n" newlines: Windows text mode would write "\r\n" and use the console code page.
    stdin = open(sys.stdin.fileno(), encoding="utf-8", errors="replace", newline="\n", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)
    serve(Server(sheet, args.log), stdin, stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
