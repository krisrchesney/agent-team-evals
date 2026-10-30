"""Small text-layout helpers used by the renderers."""


def column_widths(headers, rows):
    """Width of each column: its longest cell, header included."""
    return [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]


def align_row(cells, widths, left_columns=(0,)):
    """Pad `cells` to `widths`; columns listed in `left_columns` are left-aligned, the rest right-aligned."""
    out = []
    for i, (cell, width) in enumerate(zip(cells, widths)):
        out.append(cell.ljust(width) if i in left_columns else cell.rjust(width))
    return out


def rule(widths, char="-"):
    return [char * w for w in widths]


def indent(text, prefix="  "):
    """Prefix every non-empty line of `text`."""
    return "\n".join(prefix + line if line else line for line in text.splitlines())
