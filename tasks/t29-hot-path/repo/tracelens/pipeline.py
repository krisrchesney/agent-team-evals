"""The whole analysis in one call."""
from .analysis.funnel import funnel
from .analysis.sessions import DEFAULT_GAP_MS, bounce_rate, sessionize
from .ingest.dedupe import dedupe
from .reports.pages import top_pages


def run(events, gap_ms=DEFAULT_GAP_MS, funnel_steps=(), top_n=10):
    unique = dedupe(events)
    sessions = sessionize(unique, gap_ms)
    return {
        "events": len(unique),
        "duplicates": len(events) - len(unique),
        "sessions": len(sessions),
        "bounce_rate": bounce_rate(sessions),
        "top_pages": top_pages(unique, top_n),
        "funnel": funnel(unique, list(funnel_steps)),
    }
