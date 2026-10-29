"""Turn aggregated results into report text."""
import csv
import io


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


def render(results, key_header, value_header):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([key_header, value_header])
    for group in sorted(results):
        writer.writerow([group, format_value(results[group])])
    return buf.getvalue().rstrip("\n")
