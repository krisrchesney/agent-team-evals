"""Stop hook: before Claude ends a turn in this repo, run scripts/check.py.

Same pattern as Boxwatch. Exit code 2 + a message on stderr blocks the stop and hands
the failure back to Claude. When `stop_hook_active` is true (Claude is already continuing
because of this hook) we let it stop, so an unfixable check can't loop forever.
scripts/check.py makes no API calls, so this hook never spends money.
"""

import json
import os
import subprocess
import sys

event = json.load(sys.stdin)
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
if not status.stdout.strip():
    sys.exit(0)

result = subprocess.run([sys.executable, os.path.join(root, "scripts", "check.py")],
                        cwd=root, capture_output=True, text=True)
if result.returncode == 0 or event.get("stop_hook_active"):
    sys.exit(0)

tail = (result.stdout + result.stderr)[-3000:]
print(f"scripts/check.py failed. Fix it before stopping:\n{tail}", file=sys.stderr)
sys.exit(2)
