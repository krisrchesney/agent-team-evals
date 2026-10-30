"""Plain-text report for a plan."""


def format_size(count):
    """Size in bytes."""
    return f"{count} B"


def format_report(steps):
    """The plan as text, one `name version` line per step, every line ending in a newline."""
    return "".join(f"{step.name} {step.version}\n" for step in steps)
