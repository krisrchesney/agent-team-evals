"""Lines are split on "\n" only (a "\r" stays in the line). Every line keeps its "\n", except possibly the
last one of a text that does not end with a newline."""


def split_lines(text):
    parts = text.split("\n")
    lines = [p + "\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def join_lines(lines):
    return "".join(lines)
