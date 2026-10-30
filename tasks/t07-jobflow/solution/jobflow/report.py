"""Turn results into text or JSON-ready dicts."""


def render(results):
    lines = []
    for r in results:
        line = f"{r.name}: {r.status}"
        if r.status == "failed":
            line += f": {r.error}"
        elif r.status == "skipped":
            line += f": {r.reason}"
        if r.status != "skipped" and r.attempts > 1:
            line += f" ({r.attempts} attempts)"
        lines.append(line)
    counts = {s: sum(1 for r in results if r.status == s) for s in ("ok", "failed", "skipped")}
    lines.append(f"{len(results)} jobs: {counts['ok']} ok, {counts['failed']} failed, "
                 f"{counts['skipped']} skipped")
    return "\n".join(lines)


def to_dicts(results):
    return [
        {"name": r.name, "status": r.status, "output": r.output, "error": r.error,
         "reason": r.reason, "attempts": r.attempts, "stage": r.stage}
        for r in results
    ]
