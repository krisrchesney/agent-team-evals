"""parse -> filters -> transforms -> format."""
from .filters import build_filter
from .formats import get_format
from .parse import parse_lines
from .transforms import build_transform


def run_pipeline(lines, filters=(), transforms=(), fmt="text"):
    """Return the output lines. Every filter must pass; transforms run in the order given."""
    preds = [build_filter(spec) for spec in filters]
    steps = [build_transform(spec) for spec in transforms]
    render = get_format(fmt)
    out = []
    for rec in parse_lines(lines):
        if not all(pred(rec) for pred in preds):
            continue
        for step in steps:
            rec = step(rec)
        out.append(render(rec))
    return out
