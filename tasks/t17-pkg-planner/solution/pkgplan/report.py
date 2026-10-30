"""Plain-text report for a plan."""
from decimal import ROUND_HALF_UP, Decimal

_UNITS = ("B", "KiB", "MiB", "GiB")


def format_size(count):
    """Human-readable size: whole bytes below 1 KiB, otherwise one decimal, rounded half up."""
    if count < 0:
        raise ValueError("size cannot be negative")
    if count < 1024:
        return f"{count} B"
    unit = 1
    while unit < 3 and count >= 1024 ** (unit + 1):
        unit += 1

    def shown(u):
        return (Decimal(count) / Decimal(1024 ** u)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    value = shown(unit)
    if value >= 1024 and unit < 3:  # e.g. 1023.96 KiB would print as 1024.0 KiB: use the next unit
        unit += 1
        value = shown(unit)
    return f"{value} {_UNITS[unit]}"


def format_report(steps):
    """The plan as text, one line per row, every line ending in a newline."""
    warnings = [f"warning: {s.name} {s.version} is yanked" for s in sorted(steps, key=lambda s: s.key) if s.yanked]
    if all(s.action == "keep" for s in steps):
        return "".join(line + "\n" for line in ["Nothing to do.", *warnings])
    counts = {a: sum(1 for s in steps if s.action == a) for a in ("install", "upgrade", "downgrade", "keep")}
    lines = ["Plan: {install} install, {upgrade} upgrade, {downgrade} downgrade, {keep} keep".format(**counts)]
    sizes = ["-" if s.action == "keep" else format_size(s.size) for s in steps]
    index_w = len(str(len(steps)))
    name_w = max(len(s.name) for s in steps)
    version_w = max(len(str(s.version)) for s in steps)
    size_w = max(len(text) for text in sizes)
    for i, (step, size) in enumerate(zip(steps, sizes), start=1):
        lines.append(f"{i:>{index_w}}. {step.name:<{name_w}} {str(step.version):<{version_w}} "
                     f"{step.action:<9} {size:>{size_w}}")
    total = sum(s.size for s in steps if s.action != "keep")
    lines.append(f"Total download: {format_size(total)}")
    return "".join(line + "\n" for line in [*lines, *warnings])
