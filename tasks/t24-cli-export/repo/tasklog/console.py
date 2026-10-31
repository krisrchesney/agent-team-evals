import json


class Console:
    """Everything the tool prints goes through here."""

    def __init__(self, stdout, stderr, quiet=False, as_json=False, command=None):
        self.stdout = stdout
        self.stderr = stderr
        self.quiet = quiet
        self.as_json = as_json
        self.command = command

    def say(self, text):
        if not self.quiet and not self.as_json:
            print(text, file=self.stdout)

    def emit(self, payload):
        if self.as_json:
            print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), file=self.stdout)

    def warn(self, message):
        print(f"tasklog: warning: {message}", file=self.stderr)

    def error(self, err):
        if self.as_json:
            body = {"command": self.command, "error": {"code": err.code, "message": err.message}}
            print(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False), file=self.stderr)
        else:
            print(f"tasklog: error: {err.message}", file=self.stderr)
