"""parse -> filters -> transforms -> format."""
from .filters import build_filter
from .formats import get_format
from .parse import parse_lines
from .transforms import build_transform


def run_pipeline(lines, filters=(), transforms=(), fmt="text", lenient=False, stats=None):
    """Return the output lines. Every filter must pass; transforms run in the order given and may
    drop a record. If `stats` is a dict it is filled with the run's counts."""
    preds = [build_filter(spec) for spec in filters]
    steps = [build_transform(spec) for spec in transforms]  # fresh state for this run
    render = get_format(fmt)
    counts = dict.fromkeys(("read", "skipped", "filtered", "deduped", "emitted"), 0)

    def skip(_error):
        counts["skipped"] += 1

    out = []
    for rec in parse_lines(lines, skip if lenient else None):
        counts["read"] += 1
        if not all(pred(rec) for pred in preds):
            counts["filtered"] += 1
            continue
        for step in steps:
            rec = step(rec)
            if rec is None:
                counts["deduped"] += 1
                break
        else:
            out.append(render(rec))
            counts["emitted"] += 1
    if stats is not None:
        stats.clear()
        stats.update(counts)
    return out
