"""Exporting results."""
import csv
import io
import json


def results_csv(searcher, result):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["rank", "id", "score", "title", "tags"])
    for rank, hit in enumerate(result.hits, start=1):
        doc = searcher.index.get(hit.id)
        writer.writerow([rank, hit.id, f"{hit.score:.3f}", doc.title, ";".join(doc.tags)])
    return out.getvalue()


def results_json(searcher, result):
    rows = []
    for hit in result.hits:
        doc = searcher.index.get(hit.id)
        rows.append({"id": hit.id, "score": hit.score, "title": doc.title, "highlights": hit.highlights})
    return json.dumps({"query": result.query, "total": result.total, "hits": rows}, indent=2)
