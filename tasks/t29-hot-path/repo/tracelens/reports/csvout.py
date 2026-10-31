"""Reports as CSV text."""
import csv
import io


def rows_to_csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def pages_csv(rows):
    return rows_to_csv(["page", "views"], rows)


def sessions_csv(sessions):
    return rows_to_csv(
        ["session", "user", "start", "end", "events", "pages"],
        [(s.id, s.user, s.start, s.end, s.events, "|".join(s.pages)) for s in sessions],
    )


def funnel_csv(steps, reached):
    rows = []
    for i, (name, count) in enumerate(zip(steps, reached)):
        share = count / reached[0] if reached and reached[0] else 0.0
        rows.append((i + 1, name, count, f"{share:.3f}"))
    return rows_to_csv(["step", "page", "users", "share"], rows)
